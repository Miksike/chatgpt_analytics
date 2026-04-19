from pathlib import Path


def find_workspace_root() -> Path:
    """Return the project root based on this file's location."""
    return Path(__file__).resolve().parent.parent


def main() -> None:
    # The workspace root is the parent of the scripts folder.
    workspace_root = find_workspace_root()
    raw_export_dir = workspace_root / "raw_export"

    print(f"Workspace root: {workspace_root}")

    # Stop early if the expected export folder is missing.
    if not raw_export_dir.exists():
        print("raw_export does not exist.")
        return

    print(f"Contents of {raw_export_dir}:")

    # Print all files and folders in a stable, readable order.
    for item in sorted(raw_export_dir.iterdir(), key=lambda path: (path.is_file(), path.name.lower())):
        item_type = "FILE" if item.is_file() else "DIR"
        print(f"[{item_type}] {item.name}")


if __name__ == "__main__":
    main()