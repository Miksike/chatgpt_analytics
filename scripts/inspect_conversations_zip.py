from pathlib import Path
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
    print(f"Inspecting ZIP: {zip_path}\n")

    with zipfile.ZipFile(zip_path, "r") as zf:
        infos = zf.infolist()
        print(f"Files in ZIP: {len(infos)}\n")

        interesting_suffixes = {".json", ".html", ".csv", ".txt", ".md"}
        interesting = []

        for info in infos:
            name = info.filename
            suffix = Path(name).suffix.lower()
            if suffix in interesting_suffixes:
                interesting.append(info)

        print(f"Interesting structured files found: {len(interesting)}\n")

        for info in interesting[:300]:
            size_mb = info.file_size / (1024 * 1024)
            print(f"{info.filename} ({size_mb:.3f} MB)")


if __name__ == "__main__":
    main()