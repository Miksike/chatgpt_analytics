from pathlib import Path
import sys

log_file = Path(r"C:\Users\Roomelt Needo\OneDrive - Kurmik AS\Dokumendid\AAA CHATGPT\shared_log.txt")

if not log_file.exists():
    print("Logifaili ei leitud.")
    raise SystemExit(1)

line_count = 10
if len(sys.argv) >= 2:
    try:
        line_count = int(sys.argv[1])
    except ValueError:
        print("Anna esimese argumendina ridade arv, näiteks: python read_log.py 5")
        raise SystemExit(1)

lines = log_file.read_text(encoding="utf-8").splitlines()
tail = lines[-line_count:]

print(f"Viimased {len(tail)} rida failist {log_file}:")
for line in tail:
    print(line)