"""
Sandbox File Tracker - tracks files written to the E2B sandbox during a session.

Parses bash tool call commands for file-writing patterns (heredoc, tee, python open(),
redirect) and maintains a lightweight manifest. This manifest is injected into context
so the model knows what's on disk without replaying full file content.
"""
import re
from typing import Dict, List, Optional

# Patterns that write files
_HEREDOC_WRITE = re.compile(
    r"cat\s+>>\s*(\S+)\s*<<\s*['\"]?(\w+)['\"]?\n(.*?)\n\2",
    re.DOTALL,
)
_HEREDOC_OVERWRITE = re.compile(
    r"cat\s+>\s*(\S+)\s*<<\s*['\"]?(\w+)['\"]?\n(.*?)\n\2",
    re.DOTALL,
)
_TEE_WRITE = re.compile(r"tee\s+(?:-a\s+)?(\S+)")
_REDIRECT_WRITE = re.compile(r">\s*(\S+\.(?:py|sh|js|ts|csv|json|md|html|txt|yaml|yml|toml|cfg|sql))")
_PYTHON_OPEN = re.compile(r"open\(['\"]([^'\"]+)['\"],\s*['\"]w")
_MV_RENAME = re.compile(r"mv\s+(?:-\w+\s+)*(\S+)\s+(\S+)")
_RM_DELETE = re.compile(r"rm\s+(?:-\w+\s+)*([^\s;|&]+(?:\s+[^\s;|&]+)*)")


class SandboxFileTracker:
    """Tracks files written to the sandbox during a session."""

    def __init__(self):
        self._files: Dict[str, dict] = {}
        self._turn: int = 0

    def next_turn(self):
        self._turn += 1

    def process_bash_command(self, cmd: str, tool_call_id: Optional[str] = None):
        if not cmd:
            return

        for pattern in (_HEREDOC_OVERWRITE, _HEREDOC_WRITE):
            for m in pattern.finditer(cmd):
                filepath = m.group(1)
                body = m.group(3)
                line_count = body.count("\n") + 1
                self._files[filepath] = {
                    "lines": line_count,
                    "turn": self._turn,
                    "method": "heredoc",
                }

        for m in _TEE_WRITE.finditer(cmd):
            self._files[m.group(1)] = {"turn": self._turn, "method": "tee"}

        for m in _REDIRECT_WRITE.finditer(cmd):
            self._files[m.group(1)] = {"turn": self._turn, "method": "redirect"}

        for m in _PYTHON_OPEN.finditer(cmd):
            self._files[m.group(1)] = {"turn": self._turn, "method": "python"}

        for m in _MV_RENAME.finditer(cmd):
            src, dst = m.group(1), m.group(2)
            if src in self._files:
                self._files[dst] = {**self._files.pop(src), "turn": self._turn}

        for m in _RM_DELETE.finditer(cmd):
            for f in m.group(1).split():
                f = f.strip()
                self._files.pop(f, None)

    def track_file(self, filepath: str, line_count: int = 0, method: str = "unknown"):
        info = {"turn": self._turn, "method": method}
        if line_count:
            info["lines"] = line_count
        self._files[filepath] = info

    def get_manifest(self) -> str:
        if not self._files:
            return ""

        lines = ["<sandbox_files>"]
        for path, info in sorted(self._files.items()):
            parts = [path]
            if "lines" in info:
                parts.append(f"{info['lines']} lines")
            parts.append(f"turn {info['turn']}")
            lines.append(f"  {' | '.join(parts)}")
        lines.append("</sandbox_files>")
        return "\n".join(lines)

    @property
    def file_count(self) -> int:
        return len(self._files)
