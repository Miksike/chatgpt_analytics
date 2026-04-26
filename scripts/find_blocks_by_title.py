from pathlib import Path
import csv


TARGET_TITLES = [
    "2026-N11",
    "Päkk ja mehhaanika",
    "Projektide parandused eksperdi järgi",
    "OneDrive konto vahetamine",
    "Vastuskiri pinnase olukorrast",
    "Elektriauto valiku juhend",
]


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def main():
    root = find_workspace_root()
    manifest_path = root / "working_data" / "conversation_blocks_for_mode_discovery_manifest.csv"

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded rows: {len(rows)}")

    for target in TARGET_TITLES:
        target_norm = normalize(target)
        matches = [
            row for row in rows
            if normalize(row.get("conversation_title")) == target_norm
        ]

        if not matches:
            # fallback: partial title match
            matches = [
                row for row in rows
                if target_norm in normalize(row.get("conversation_title"))
            ]

        print("\n" + "=" * 100)
        print(f"TARGET: {target}")
        print(f"MATCHES: {len(matches)}")

        for row in matches:
            print(
                f"- block_id={row.get('block_id')} | "
                f"title={row.get('conversation_title')} | "
                f"container={row.get('container_label') or 'NO_CONTAINER'} | "
                f"status={row.get('container_status')} | "
                f"block={row.get('block_index')}/{row.get('block_count')} | "
                f"chars={row.get('chars_total')} | "
                f"messages={row.get('message_count')}"
            )
            print(f"  first: {row.get('first_user_excerpt')}")
            print(f"  last:  {row.get('last_user_excerpt')}")


if __name__ == "__main__":
    main()