import pandas as pd
from pathlib import Path


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
    out_path = root / "working_data" / "conversation_summary.csv"

    df = pd.read_csv(in_path)

    # Tüüpide korrastus
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["length"] = pd.to_numeric(df["length"], errors="coerce").fillna(0).astype(int)

    # Ainult sisulised read
    df = df[df["role"].isin(["user", "assistant"])].copy()
    df["text"] = df["text"].apply(clean_text)
    df = df[df["text"].notna()].copy()

    # Järjestame vestluse sees ajaliselt
    df = df.sort_values(["conversation_id", "timestamp", "node_id"], na_position="last").copy()

    # Esimene kasutaja sõnum vestluses
    first_user_df = (
        df[df["role"] == "user"]
        .sort_values(["conversation_id", "timestamp", "node_id"], na_position="last")
        .groupby("conversation_id", as_index=False)
        .first()[["conversation_id", "text", "timestamp"]]
        .rename(columns={
            "text": "first_user_text",
            "timestamp": "first_user_timestamp"
        })
    )

    # Viimane kasutaja sõnum vestluses
    last_user_df = (
        df[df["role"] == "user"]
        .sort_values(["conversation_id", "timestamp", "node_id"], na_position="last")
        .groupby("conversation_id", as_index=False)
        .last()[["conversation_id", "timestamp"]]
        .rename(columns={"timestamp": "last_user_timestamp"})
    )

    # Esimene assistendi sõnum vestluses
    first_assistant_df = (
        df[df["role"] == "assistant"]
        .sort_values(["conversation_id", "timestamp", "node_id"], na_position="last")
        .groupby("conversation_id", as_index=False)
        .first()[["conversation_id", "timestamp"]]
        .rename(columns={"timestamp": "first_assistant_timestamp"})
    )

    # Viimane assistendi sõnum vestluses
    last_assistant_df = (
        df[df["role"] == "assistant"]
        .sort_values(["conversation_id", "timestamp", "node_id"], na_position="last")
        .groupby("conversation_id", as_index=False)
        .last()[["conversation_id", "timestamp"]]
        .rename(columns={"timestamp": "last_assistant_timestamp"})
    )

    # Põhikokkuvõte
    summary = (
        df.groupby("conversation_id", as_index=False)
        .agg(
            title=("title", "first"),
            first_timestamp=("timestamp", "min"),
            last_timestamp=("timestamp", "max"),
            message_count=("text", "count"),
            user_messages=("role", lambda x: (x == "user").sum()),
            assistant_messages=("role", lambda x: (x == "assistant").sum()),
            total_chars=("length", "sum"),
            max_message_chars=("length", "max"),
            min_message_chars=("length", "min"),
        )
    )

    # Lisame detailväljad
    summary = summary.merge(first_user_df, on="conversation_id", how="left")
    summary = summary.merge(last_user_df, on="conversation_id", how="left")
    summary = summary.merge(first_assistant_df, on="conversation_id", how="left")
    summary = summary.merge(last_assistant_df, on="conversation_id", how="left")

    # Tuletatud väljad
    summary["duration_minutes"] = (
        (summary["last_timestamp"] - summary["first_timestamp"]).dt.total_seconds() / 60
    ).round(2)

    summary["avg_chars_per_message"] = (
        summary["total_chars"] / summary["message_count"]
    ).round(2)

    summary["user_share"] = (
        summary["user_messages"] / summary["message_count"]
    ).round(3)

    summary["assistant_share"] = (
        summary["assistant_messages"] / summary["message_count"]
    ).round(3)

    # Loetav järjestus
    summary = summary.sort_values("first_timestamp", na_position="last").reset_index(drop=True)

    summary.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Saved: {out_path}")
    print(f"Conversations: {len(summary)}")
    print("\nColumns:")
    for col in summary.columns:
        print(f" - {col}")

    print("\nSample:")
    print(summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()