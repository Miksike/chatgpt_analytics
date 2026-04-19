from pathlib import Path
from datetime import datetime
import sys

log_file = Path(r"C:\Users\Roomelt Needo\OneDrive - Kurmik AS\Dokumendid\AAA CHATGPT\shared_log.txt")


def add_text(text: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {text}\n")
    print(f"Lisatud: {timestamp} | {text}")


def read_lines(count: int = 10) -> None:
    if not log_file.exists():
        print("Logifaili ei leitud.")
        raise SystemExit(1)

    lines = log_file.read_text(encoding="utf-8").splitlines()
    tail = lines[-count:]

    print(f"Viimased {len(tail)} rida:")
    for line in tail:
        print(line)


def main() -> None:
    if len(sys.argv) < 2:
        print("Kasutus:")
        print('  python log_tool.py add "Tere maailm"')
        print("  python log_tool.py read 5")
        raise SystemExit(1)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print('Näide: python log_tool.py add "Tere maailm"')
            raise SystemExit(1)
        add_text(sys.argv[2])

    elif command == "read":
        count = 10
        if len(sys.argv) >= 3:
            try:
                count = int(sys.argv[2])
            except ValueError:
                print("Ridade arv peab olema täisarv.")
                raise SystemExit(1)
        read_lines(count)

    else:
        print(f"Tundmatu käsk: {command}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()