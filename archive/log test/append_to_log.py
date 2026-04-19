from pathlib import Path
from datetime import datetime
import sys

log_file = Path(r"C:\Users\Roomelt Needo\OneDrive - Kurmik AS\Dokumendid\AAA CHATGPT\shared_log.txt")

log_file.parent.mkdir(parents=True, exist_ok=True)

if len(sys.argv) < 2:
    print("Anna tekst käsurea argumendina.")
    print('Näide: python append_to_log.py "Tere maailm"')
    raise SystemExit(1)

text = sys.argv[1]
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

with log_file.open("a", encoding="utf-8") as f:
    f.write(f"{timestamp} | {text}\n")

print(f"Kirjutatud faili: {log_file}")
print(f"Sisu: {timestamp} | {text}")