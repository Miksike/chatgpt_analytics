from pathlib import Path
import csv
import json


SAMPLE_BLOCK_IDS = [
    "69a4f194-5968-8391-a3fb-4c61ae3debe8::block_001",
    "69a4f194-5968-8391-a3fb-4c61ae3debe8::block_002",
    "69a4f194-5968-8391-a3fb-4c61ae3debe8::block_003",
    "698845db-df3c-8390-a719-6db41968f218::block_001",
    "68d3fe9e-6ac8-8328-b663-60b57482b410::block_001",
    "6989bb23-5388-838f-bc2d-f6d442683df0::block_001",
    "68cbaeb7-d0a8-8331-bf52-8498390e0f62::block_001",
    "685b9e97-5bd8-8013-9461-b711082cefab::block_001",
]


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
    return records


def write_jsonl(path: Path, records: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_manifest_csv(path: Path, records: list[dict]):
    fieldnames = [
        "sample_no",
        "block_id",
        "conversation_id",
        "conversation_title",
        "conversation_create_time",
        "conversation_update_time",
        "container_id",
        "container_kind",
        "container_label",
        "container_status",
        "block_index",
        "block_count",
        "is_complete_conversation",
        "message_count",
        "user_messages",
        "assistant_messages",
        "chars_total",
        "chars_user",
        "chars_assistant",
        "first_user_excerpt",
        "last_user_excerpt",
        "sample_reason",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, record in enumerate(records, start=1):
            writer.writerow(
                {
                    "sample_no": idx,
                    "block_id": record.get("block_id"),
                    "conversation_id": record.get("conversation_id"),
                    "conversation_title": record.get("conversation_title"),
                    "conversation_create_time": record.get("conversation_create_time"),
                    "conversation_update_time": record.get("conversation_update_time"),
                    "container_id": record.get("container_id"),
                    "container_kind": record.get("container_kind"),
                    "container_label": record.get("container_label"),
                    "container_status": record.get("container_status"),
                    "block_index": record.get("block_index"),
                    "block_count": record.get("block_count"),
                    "is_complete_conversation": record.get("is_complete_conversation"),
                    "message_count": record.get("message_count"),
                    "user_messages": record.get("user_messages"),
                    "assistant_messages": record.get("assistant_messages"),
                    "chars_total": record.get("chars_total"),
                    "chars_user": record.get("chars_user"),
                    "chars_assistant": record.get("chars_assistant"),
                    "first_user_excerpt": record.get("first_user_excerpt"),
                    "last_user_excerpt": record.get("last_user_excerpt"),
                    "sample_reason": record.get("sample_reason"),
                }
            )


def main():
    root = find_workspace_root()
    working_data_dir = root / "working_data"

    input_jsonl = working_data_dir / "conversation_blocks_for_mode_discovery.jsonl"

    output_jsonl = working_data_dir / "manual_mode_discovery_sample.jsonl"
    output_manifest = working_data_dir / "manual_mode_discovery_sample_manifest.csv"

    if not input_jsonl.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")

    all_records = load_jsonl(input_jsonl)
    by_block_id = {record.get("block_id"): record for record in all_records}

    missing = [block_id for block_id in SAMPLE_BLOCK_IDS if block_id not in by_block_id]
    if missing:
        print("Missing block_ids:")
        for block_id in missing:
            print(f" - {block_id}")
        raise SystemExit("Cannot build sample because some block_ids are missing.")

    selected = []
    for idx, block_id in enumerate(SAMPLE_BLOCK_IDS, start=1):
        record = dict(by_block_id[block_id])

        if record.get("conversation_title") == "2026-N11":
            sample_reason = (
                "Manual seed sample: Ajaplaneerimise tööruum; included all three blocks "
                "to preserve the internal structure of a long operational proto-PeOp week conversation."
            )
        elif record.get("conversation_title") == "Päkk ja mehhaanika":
            sample_reason = "Manual seed sample: embodied/mechanical reasoning inside a current workspace."
        elif record.get("conversation_title") == "Projektide parandused eksperdi järgi":
            sample_reason = "Manual seed sample: archived project, expert review and document correction workflow."
        elif record.get("conversation_title") == "OneDrive konto vahetamine":
            sample_reason = "Manual seed sample: digital infrastructure/tooling friction in a no-container conversation."
        elif record.get("conversation_title") == "Vastuskiri pinnase olukorrast":
            sample_reason = "Manual seed sample: professional communication and decision support in no-container context."
        elif record.get("conversation_title") == "Elektriauto valiku juhend":
            sample_reason = "Manual seed sample: older decision-support project capsule."
        else:
            sample_reason = "Manual seed sample."

        record["sample_no"] = idx
        record["sample_reason"] = sample_reason
        selected.append(record)

    write_jsonl(output_jsonl, selected)
    write_manifest_csv(output_manifest, selected)

    print("\nDone.")
    print(f"Input records: {len(all_records)}")
    print(f"Selected records: {len(selected)}")
    print(f"Saved JSONL: {output_jsonl}")
    print(f"Saved manifest: {output_manifest}")

    print("\nSelected sample:")
    for record in selected:
        print(
            f"- {record['sample_no']:02d} | "
            f"{record.get('block_id')} | "
            f"{record.get('conversation_title')} | "
            f"{record.get('container_label') or 'NO_CONTAINER'} | "
            f"block {record.get('block_index')}/{record.get('block_count')} | "
            f"chars={record.get('chars_total')}"
        )


if __name__ == "__main__":
    main()