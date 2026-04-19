from pathlib import Path
import json
import zipfile
import pandas as pd


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def extract_text(message):
    if not message:
        return None

    content = message.get("content")
    if not content:
        return None

    parts = content.get("parts")
    if not parts:
        return None

    # enamasti üks tekstiplokk
    return "\n".join(str(p) for p in parts if p)


def main():
    workspace_root = find_workspace_root()
    raw_export_dir = workspace_root / "raw_export"
    out_path = workspace_root / "working_data" / "messages.csv"
    out_path.parent.mkdir(exist_ok=True)

    zip_path = list(raw_export_dir.rglob("*chatgpt-*.zip"))[0]

    rows = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = sorted([n for n in zf.namelist() if n.startswith("conversations-")])

        for jf in json_files:
            print(f"Processing {jf}")

            with zf.open(jf) as f:
                conversations = json.load(f)

            for conv in conversations:
                conv_id = conv.get("conversation_id")
                title = conv.get("title")

                mapping = conv.get("mapping", {})

                for node_id, node in mapping.items():
                    message = node.get("message")
                    if not message:
                        continue

                    role = message.get("author", {}).get("role")
                    timestamp = message.get("create_time")

                    text = extract_text(message)

                    rows.append({
                        "conversation_id": conv_id,
                        "title": title,
                        "node_id": node_id,
                        "parent": node.get("parent"),
                        "role": role,
                        "timestamp": timestamp,
                        "text": text,
                        "length": len(text) if text else 0
                    })

    df = pd.DataFrame(rows)

    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")

    df.to_csv(out_path, index=False)

    print(f"\nSaved: {out_path}")
    print(f"Rows: {len(df)}")


if __name__ == "__main__":
    main()