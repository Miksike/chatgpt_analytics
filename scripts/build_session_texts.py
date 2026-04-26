from pathlib import Path
import json
import pandas as pd


SESSION_GAP_MINUTES = 60


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def clean_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def format_message(row) -> str:
    role = row["role"]
    timestamp = row["timestamp"]
    text = row["text"]

    return f"[{timestamp}] {role.upper()}:\n{text}"


def main():
    root = find_workspace_root()
    in_path = root / "working_data" / "messages.csv"
    out_path = root / "working_data" / "session_texts.jsonl"

    df = pd.read_csv(in_path)

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["length"] = pd.to_numeric(df["length"], errors="coerce").fillna(0).astype(int)

    df = df[df["role"].isin(["user", "assistant"])].copy()
    df["text"] = df["text"].apply(clean_text)
    df = df[df["text"].notna()].copy()
    df = df[df["timestamp"].notna()].copy()

    df = df.sort_values(
        ["conversation_id", "timestamp", "node_id"],
        na_position="last"
    ).copy()

    # Sama sessiooniloogika nagu session_summary skriptis
    df["prev_timestamp"] = df.groupby("conversation_id")["timestamp"].shift(1)
    df["gap_minutes"] = (
        (df["timestamp"] - df["prev_timestamp"]).dt.total_seconds() / 60
    )

    df["new_session"] = (
        df["prev_timestamp"].isna()
        | (df["gap_minutes"] > SESSION_GAP_MINUTES)
    )

    df["session_id"] = (
        df.groupby("conversation_id")["new_session"]
        .cumsum()
        .astype(int)
    )

    group_cols = ["conversation_id", "session_id"]

    records_written = 0

    with out_path.open("w", encoding="utf-8") as f:
        for (conversation_id, session_id), group in df.groupby(group_cols):
            group = group.sort_values(["timestamp", "node_id"])

            session_start = group["timestamp"].min()
            session_end = group["timestamp"].max()

            text_block = "\n\n---\n\n".join(
                format_message(row)
                for _, row in group.iterrows()
            )

            record = {
                "global_session_id": f"{conversation_id}::{session_id}",
                "conversation_id": conversation_id,
                "session_id": int(session_id),
                "title": group["title"].iloc[0],
                "session_start": session_start.isoformat(),
                "session_end": session_end.isoformat(),
                "duration_minutes": round(
                    (session_end - session_start).total_seconds() / 60,
                    2
                ),
                "message_count": int(len(group)),
                "user_messages": int((group["role"] == "user").sum()),
                "assistant_messages": int((group["role"] == "assistant").sum()),
                "total_chars": int(group["length"].sum()),
                "text_block": text_block,
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            records_written += 1

    print(f"Saved: {out_path}")
    print(f"Sessions written: {records_written}")
    print(f"Session gap threshold: {SESSION_GAP_MINUTES} minutes")

    print("\nSample first record:")
    with out_path.open("r", encoding="utf-8") as f:
        first_line = f.readline()
        sample = json.loads(first_line)

    print(f"global_session_id: {sample['global_session_id']}")
    print(f"title: {sample['title']}")
    print(f"session_start: {sample['session_start']}")
    print(f"session_end: {sample['session_end']}")
    print(f"message_count: {sample['message_count']}")
    print("\ntext_block preview:")
    print(sample["text_block"][:1500])


if __name__ == "__main__":
    main()