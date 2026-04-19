import pandas as pd
from pathlib import Path


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def first_user_text_in_group(group: pd.DataFrame):
    user_rows = group[group["role"] == "user"]
    if user_rows.empty:
        return None
    return user_rows.iloc[0]["text"]


def main():
    root = find_workspace_root()
    in_path = root / "working_data" / "messages.csv"
    out_path = root / "working_data" / "conversation_summary.csv"

    df = pd.read_csv(in_path)

    # Tüüpide korrastus
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["length"] = pd.to_numeric(df["length"], errors="coerce").fillna(0).astype(int)

    # Hoiame ainult sisulised read
    df = df[df["role"].isin(["user", "assistant"])].copy()
    df = df[df["text"].notna()].copy()

    # Ajaliselt järjestusse
    df = df.sort_values(["conversation_id", "timestamp"], na_position="last")

    # Põhiagregatsioon
    summary = (
        df.groupby("conversation_id")
        .agg(
            title=("title", "first"),
            first_timestamp=("timestamp", "min"),
            last_timestamp=("timestamp", "max"),
            message_count=("text", "count"),
            user_messages=("role", lambda x: (x == "user").sum()),
            assistant_messages=("role", lambda x: (x == "assistant").sum()),
            total_chars=("length", "sum"),
        )
        .reset_index()
    )

    # Esimene kasutaja sõnum eraldi, sest seda ei tasu võtta kogu grupi esimesest reast
    first_user = (
        df.groupby("conversation_id", group_keys=False)
        .apply(first_user_text_in_group)
        .reset_index(name="first_user_text")
    )

    summary = summary.merge(first_user, on="conversation_id", how="left")

    summary.to_csv(out_path, index=False)

    print(f"Saved: {out_path}")
    print(f"Conversations: {len(summary)}")
    print("\nSample:")
    print(summary.head(10).to_string(index=False))


if __name__ == "__main__":
    main()