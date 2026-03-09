"""
Build and publish the Finch E2B sandbox template.

Run from the repo root or backend/sandbox/:
    python backend/sandbox/build_template.py

After it finishes, copy the printed template ID into your .env:
    E2B_TEMPLATE_ID=<id>

The template bakes in all pip packages so sandboxes start clean every time
with no runtime pip install required.

To add a new package:
1. Add it to the RUN pip install line in e2b.Dockerfile
2. Also add it to the skill's SKILL.md `requires.bins` list (for documentation)
3. Re-run this script to publish a new template version
4. Update E2B_TEMPLATE_ID in .env with the new ID
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    from e2b import Template, default_build_logger

    api_key = os.getenv("E2B_API_KEY")
    if not api_key:
        # Try loading from backend/.env
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("E2B_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not api_key:
        print("ERROR: E2B_API_KEY not set. Export it or add it to backend/.env")
        sys.exit(1)

    dockerfile = Path(__file__).parent / "e2b.Dockerfile"
    if not dockerfile.exists():
        print(f"ERROR: e2b.Dockerfile not found at {dockerfile}")
        sys.exit(1)

    template_name = "finch-sandbox"
    print(f"Building E2B template '{template_name}' from {dockerfile} ...")
    print("This takes ~2-5 minutes on first build, ~1 minute for rebuilds.\n")

    template = Template().from_dockerfile(str(dockerfile))

    # Template.build is synchronous (not a coroutine)
    result = Template.build(
        template,
        template_name,
        cpu_count=2,
        memory_mb=1024,
        on_build_logs=default_build_logger(),
        api_key=api_key,
    )

    print(f"\nTemplate built successfully.")
    print(f"Template ID:   {result.template_id}")
    print(f"Template name: {result.name}")
    print(f"\nAdd to your .env:")
    print(f"  E2B_TEMPLATE_ID={result.template_id}")


if __name__ == "__main__":
    main()
