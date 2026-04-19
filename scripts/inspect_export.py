from pathlib import Path


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    workspace_root = find_workspace_root()
    raw_export_dir = workspace_root / "raw_export"

    print(f"Workspace root: {workspace_root}")

    if not raw_export_dir.exists():
        print("raw_export does not exist.")
        return

    print(f"\nRecursive contents of {raw_export_dir}:\n")

    for path in sorted(raw_export_dir.rglob("*"), key=lambda p: (str(p.relative_to(raw_export_dir)).count("\\"), str(p.relative_to(raw_export_dir)).lower())):
        rel = path.relative_to(raw_export_dir)
        depth = len(rel.parts) - 1
        indent = "    " * depth
        item_type = "FILE" if path.is_file() else "DIR"

        if path.is_file():
            size_kb = path.stat().st_size / 1024
            print(f"{indent}[{item_type}] {rel.name} ({size_kb:.1f} KB)")
        else:
            print(f"{indent}[{item_type}] {rel.name}")


if __name__ == "__main__":
    main()