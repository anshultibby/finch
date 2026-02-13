import argparse
import json
from typing import Any, Dict, List, Set

from sqlalchemy import select

from database import SessionLocal
from models.db import ChatMessage
from modules.agent.message_processor import enforce_tool_call_sequence


def _parse_content_blocks(content: Any) -> List[Dict[str, Any]]:
    if isinstance(content, list):
        return [c for c in content if isinstance(c, dict)]
    if isinstance(content, str) and content.strip().startswith("["):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return [c for c in parsed if isinstance(c, dict)]
        except json.JSONDecodeError:
            return []
    return []


def _extract_tool_use_ids(content: Any) -> Set[str]:
    tool_use_ids: Set[str] = set()
    for block in _parse_content_blocks(content):
        if block.get("type") == "tool_use":
            tool_use_id = block.get("id") or block.get("tool_use_id")
            if tool_use_id:
                tool_use_ids.add(tool_use_id)
    return tool_use_ids


def _format_content_preview(content: Any, limit: int = 240) -> str:
    if content is None:
        return ""
    text = content if isinstance(content, str) else json.dumps(content)
    text = text.replace("\n", "\\n")
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _validate_tool_sequences(messages: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    for idx, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        tool_calls = msg.get("tool_calls") or []
        tool_call_ids = {tc.get("id") for tc in tool_calls if tc.get("id")}
        tool_use_ids = _extract_tool_use_ids(msg.get("content"))
        expected_ids = tool_call_ids | tool_use_ids
        if not expected_ids:
            continue

        j = idx + 1
        seen_ids: Set[str] = set()
        while j < len(messages) and messages[j].get("role") == "tool":
            tool_call_id = messages[j].get("tool_call_id")
            if tool_call_id:
                seen_ids.add(tool_call_id)
            j += 1

        if seen_ids != expected_ids:
            issues.append(
                f"messages[{idx}] expected={sorted(expected_ids)} seen={sorted(seen_ids)} next_roles="
                f"{[m.get('role') for m in messages[idx+1:j+1]]}"
            )
    return issues


def dump_history(chat_id: str, output_path: str) -> None:
    db = SessionLocal()
    try:
        result = db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat_id)
            .order_by(ChatMessage.sequence.asc())
        )
        rows = list(result.scalars().all())
    finally:
        db.close()

    messages: List[Dict[str, Any]] = []
    for row in rows:
        messages.append(
            {
                "id": row.id,
                "sequence": row.sequence,
                "role": row.role,
                "content": row.content,
                "tool_calls": row.tool_calls,
                "tool_call_id": row.tool_call_id,
                "name": row.name,
            }
        )

    issues = _validate_tool_sequences(messages)
    cleaned = enforce_tool_call_sequence(messages)
    cleaned_issues = _validate_tool_sequences(cleaned)

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(f"Chat ID: {chat_id}\n")
        handle.write(f"Total messages: {len(messages)}\n")
        handle.write(f"Tool sequence issues: {len(issues)}\n")
        for issue in issues:
            handle.write(f"  - {issue}\n")
        handle.write(f"After enforce_tool_call_sequence: {len(cleaned)} messages\n")
        handle.write(f"Remaining issues after cleaning: {len(cleaned_issues)}\n")
        for issue in cleaned_issues:
            handle.write(f"  - {issue}\n")
        handle.write("\n=== FULL HISTORY ===\n")

        for msg in messages:
            tool_calls = msg.get("tool_calls") or []
            tool_call_ids = [tc.get("id") for tc in tool_calls if tc.get("id")]
            tool_use_ids = sorted(_extract_tool_use_ids(msg.get("content")))
            handle.write(
                f"\n[seq={msg['sequence']} id={msg['id']} role={msg['role']}]\n"
            )
            if tool_call_ids:
                handle.write(f"tool_calls: {tool_call_ids}\n")
            if tool_use_ids:
                handle.write(f"tool_use_ids: {tool_use_ids}\n")
            if msg.get("tool_call_id"):
                handle.write(f"tool_call_id: {msg['tool_call_id']}\n")
            if msg.get("name"):
                handle.write(f"name: {msg['name']}\n")
            handle.write(f"content_preview: {_format_content_preview(msg.get('content'))}\n")
            handle.write("content_full:\n")
            if msg.get("content") is None:
                handle.write("null\n")
            elif isinstance(msg.get("content"), str):
                handle.write(msg["content"] + "\n")
            else:
                handle.write(json.dumps(msg.get("content"), ensure_ascii=True, indent=2))
                handle.write("\n")

    print(f"Wrote chat history to {output_path}")
    print(f"Found {len(issues)} tool sequence issue(s).")
    if issues:
        print("Issues:")
        for issue in issues:
            print(f"  - {issue}")
    print(f"Remaining issues after cleaning: {len(cleaned_issues)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    dump_history(args.chat_id, args.output)


if __name__ == "__main__":
    main()
