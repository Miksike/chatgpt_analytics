from pathlib import Path
import json
import zipfile
from collections import Counter, defaultdict


FIELDS_TO_CHECK = [
    "context_scopes",
    "conversation_origin",
    "conversation_template_id",
    "gizmo_type",
    "memory_scope",
    "default_model_slug",
    "is_archived",
    "is_starred",
    "is_do_not_remember",
    "atlas_mode_enabled",
]


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def short_repr(value, max_len=300):
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def main():
    root = find_workspace_root()
    raw_export_dir = root / "raw_export"

    zip_files = list(raw_export_dir.rglob("*chatgpt-*.zip"))
    if not zip_files:
        raise FileNotFoundError("Conversation ZIP file not found under raw_export.")

    zip_path = zip_files[0]

    total_conversations = 0

    field_presence = Counter()
    field_values = {field: Counter() for field in FIELDS_TO_CHECK}
    field_examples = defaultdict(list)

    unknown_keys = Counter()

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = sorted(
            name for name in zf.namelist()
            if name.startswith("conversations-") and name.endswith(".json")
        )

        for json_file in json_files:
            print(f"Processing {json_file}")

            with zf.open(json_file) as f:
                conversations = json.load(f)

            for conv in conversations:
                total_conversations += 1

                for key in conv.keys():
                    unknown_keys[key] += 1

                for field in FIELDS_TO_CHECK:
                    value = conv.get(field)

                    if value not in (None, "", [], {}):
                        field_presence[field] += 1

                        value_key = short_repr(value, max_len=200)
                        field_values[field][value_key] += 1

                        if len(field_examples[field]) < 5:
                            field_examples[field].append(
                                {
                                    "conversation_id": conv.get("conversation_id") or conv.get("id"),
                                    "title": conv.get("title"),
                                    "value": value,
                                }
                            )

    print("\nDone.")
    print(f"Total conversations: {total_conversations}")

    print("\nAll top-level keys found:")
    for key, count in unknown_keys.most_common():
        print(f" - {key}: {count}")

    print("\nField presence:")
    for field in FIELDS_TO_CHECK:
        print(f" - {field}: {field_presence[field]} / {total_conversations}")

    print("\nNon-empty values by field:")
    for field in FIELDS_TO_CHECK:
        print(f"\n### {field}")
        if not field_values[field]:
            print("  No non-empty values.")
            continue

        for value, count in field_values[field].most_common(20):
            print(f"  {count} x {value}")

        print("  Examples:")
        for example in field_examples[field]:
            print(f"    - {example['conversation_id']} | {example['title']} | {short_repr(example['value'])}")


if __name__ == "__main__":
    main()