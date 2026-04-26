import json
from pathlib import Path

INPUT_FILE = Path("working_data/session_texts_sample_60.jsonl")
OUTPUT_FILE = Path("working_data/session_texts_sample_60.txt")

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for i, s in enumerate(lines, 1):
            out.write(f"=== SESSION {i} ===\n")
            out.write(f"conversation_id: {s['conversation_id']}\n")
            out.write(f"session_id: {s['session_id']}\n")
            out.write(f"start: {s['session_start']}\n")
            out.write(f"end: {s['session_end']}\n")
            out.write(f"message_count: {s['message_count']}\n\n")

            out.write(s["text_block"].strip())
            out.write("\n\n---\n\n")

    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()