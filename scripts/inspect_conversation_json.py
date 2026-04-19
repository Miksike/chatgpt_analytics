from pathlib import Path
import json
import zipfile


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> None:
    workspace_root = find_workspace_root()
    raw_export_dir = workspace_root / "raw_export"

    zip_files = list(raw_export_dir.rglob("*chatgpt-*.zip"))
    if not zip_files:
        print("Conversation ZIP file not found.")
        return

    zip_path = zip_files[0]

    with zipfile.ZipFile(zip_path, "r") as zf:
        target_name = "conversations-000.json"
        if target_name not in zf.namelist():
            print(f"{target_name} not found in ZIP.")
            return

        with zf.open(target_name) as f:
            data = json.load(f)

    print(f"Top-level type: {type(data).__name__}")
    if isinstance(data, list):
        print(f"Items in file: {len(data)}")
        if not data:
            return

        first = data[0]
        print("\nFirst item keys:")
        for key in first.keys():
            print(f" - {key}")

        print("\nSample values:")
        for key, value in first.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                print(f"{key}: {value}")
            elif isinstance(value, list):
                print(f"{key}: LIST[{len(value)}]")
            elif isinstance(value, dict):
                print(f"{key}: DICT[{len(value)} keys]")
            else:
                print(f"{key}: {type(value).__name__}")
    else:
        print("Unexpected top-level structure.")


if __name__ == "__main__":
    main()