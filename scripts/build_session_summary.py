from pathlib import Path
import pandas as pd


SESSION_GAP_MINUTES = 60


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def clean_text(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def main():
    root = find_workspace_root()
    in_path = root / "working_data" / "messages.csv"
    out_path = root / "working_data" / "session_summary.csv"

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

    # Vahe eelmise sõnumiga sama vestluse sees
    df["prev_timestamp"] = df.groupby("conversation_id")["timestamp"].shift(1)
    df["gap_minutes"] = (
        (df["timestamp"] - df["prev_timestamp"]).dt.total_seconds() / 60
    )

    # Uus sessioon, kui:
    # 1) vestluse esimene sõnum
    # 2) paus eelmisest sõnumist > SESSION_GAP_MINUTES
    df["new_session"] = (
        df["prev_timestamp"].isna()
        | (df["gap_minutes"] > SESSION_GAP_MINUTES)
    )

    # Sessiooni järjekorranumber vestluse sees
    df["session_id"] = (
        df.groupby("conversation_id")["new_session"]
        .cumsum()
        .astype(int)
    )

    group_cols = ["conversation_id", "session_id"]

    summary = (
        df.groupby(group_cols, as_index=False)
        .agg(
            title=("title", "first"),
            session_start=("timestamp", "min"),
            session_end=("timestamp", "max"),
            message_count=("text", "count"),
            user_messages=("role", lambda x: (x == "user").sum()),
            assistant_messages=("role", lambda x: (x == "assistant").sum()),
            total_chars=("length", "sum"),
            avg_chars_per_message=("length", "mean"),
            max_message_chars=("length", "max"),
            first_text=("text", "first"),
            last_text=("text", "last"),
        )
    )

    summary["duration_minutes"] = (
        (summary["session_end"] - summary["session_start"])
        .dt.total_seconds()
        .div(60)
        .round(2)
    )

    summary["avg_chars_per_message"] = summary["avg_chars_per_message"].round(2)

    # Globaalne ID, mugav hilisemaks AI analüüsiks
    summary["global_session_id"] = (
        summary["conversation_id"].astype(str)
        + "::"
        + summary["session_id"].astype(str)
    )

    # Veergude loogiline järjestus
    summary = summary[
        [
            "global_session_id",
            "conversation_id",
            "session_id",
            "title",
            "session_start",
            "session_end",
            "duration_minutes",
            "message_count",
            "user_messages",
            "assistant_messages",
            "total_chars",
            "avg_chars_per_message",
            "max_message_chars",
            "first_text",
            "last_text",
        ]
    ]

    summary = summary.sort_values(["session_start", "conversation_id", "session_id"])
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Saved: {out_path}")
    print(f"Sessions: {len(summary)}")
    print(f"Source messages: {len(df)}")
    print(f"Session gap threshold: {SESSION_GAP_MINUTES} minutes")

    print("\nBasic stats:")
    print(f"Average duration minutes: {summary['duration_minutes'].mean():.2f}")
    print(f"Average message count: {summary['message_count'].mean():.2f}")
    print(f"Median message count: {summary['message_count'].median():.2f}")

    short = (summary["message_count"] <= 3).sum()
    medium = ((summary["message_count"] >= 4) & (summary["message_count"] <= 15)).sum()
    long = (summary["message_count"] > 15).sum()

    print("\nSession length buckets:")
    print(f"Short sessions, 1–3 messages: {short}")
    print(f"Medium sessions, 4–15 messages: {medium}")
    print(f"Long sessions, >15 messages: {long}")

    print("\nSample:")
    print(summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()