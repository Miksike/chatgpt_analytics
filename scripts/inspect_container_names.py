from pathlib import Path
import json
import re
import zipfile
from collections import defaultdict, Counter


CONTAINER_ID_PATTERN = re.compile(r"g-(?:p-)?[A-Za-z0-9]+")

STRUCTURED_SUFFIXES = {".json", ".html", ".csv", ".txt", ".md"}
MAX_FILE_SIZE_MB_TO_SCAN_AS_TEXT = 20


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def short(value, max_len=500):
    if value is None:
        return None

    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)

    text = text.replace("\n", " ").replace("\r", " ").strip()

    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def find_container_ids_in_value(value):
    text = short(value, max_len=5000)
    if not text:
        return set()
    return set(CONTAINER_ID_PATTERN.findall(text))


def walk_json(obj, path="$"):
    """
    Yield (path, value) pairs for every node in a JSON-like object.
    """
    yield path, obj

    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk_json(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk_json(value, f"{path}[{idx}]")


def collect_name_like_fields(obj):
    """
    Return likely human-readable name/title fields from a dict.
    """
    if not isinstance(obj, dict):
        return {}

    name_keys = [
        "name",
        "title",
        "display_name",
        "description",
        "workspace_name",
        "project_name",
        "gizmo_name",
        "template_name",
        "slug",
    ]

    result = {}
    for key in name_keys:
        if key in obj and obj[key] not in (None, "", [], {}):
            result[key] = obj[key]

    return result


def inspect_json_file(zf, filename, container_hits):
    with zf.open(filename) as f:
        try:
            data = json.load(f)
        except Exception as exc:
            print(f"Could not parse JSON: {filename} | {exc}")
            return

    for path, value in walk_json(data):
        ids = find_container_ids_in_value(value)
        if not ids:
            continue

        nearby_name_fields = {}

        if isinstance(value, dict):
            nearby_name_fields = collect_name_like_fields(value)

        for container_id in ids:
            container_hits[container_id].append(
                {
                    "file": filename,
                    "path": path,
                    "value_preview": short(value, max_len=1000),
                    "nearby_name_fields": nearby_name_fields,
                }
            )


def inspect_text_file(zf, info, container_hits):
    filename = info.filename
    size_mb = info.file_size / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB_TO_SCAN_AS_TEXT:
        return

    with zf.open(filename) as f:
        try:
            text = f.read().decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"Could not read text: {filename} | {exc}")
            return

    ids = set(CONTAINER_ID_PATTERN.findall(text))
    if not ids:
        return

    for container_id in ids:
        idx = text.find(container_id)
        start = max(0, idx - 500)
        end = min(len(text), idx + 500)
        preview = text[start:end].replace("\n", " ").replace("\r", " ")

        container_hits[container_id].append(
            {
                "file": filename,
                "path": "text_search",
                "value_preview": preview,
                "nearby_name_fields": {},
            }
        )


def collect_conversation_template_ids(zf):
    """
    Read conversations-*.json and collect actual conversation_template_id values
    plus example conversations for each value.
    """
    template_counts = Counter()
    template_examples = defaultdict(list)

    json_files = sorted(
        name for name in zf.namelist()
        if name.startswith("conversations-") and name.endswith(".json")
    )

    for json_file in json_files:
        with zf.open(json_file) as f:
            conversations = json.load(f)

        for conv in conversations:
            template_id = conv.get("conversation_template_id")
            if template_id in (None, "", [], {}):
                continue

            template_counts[template_id] += 1

            if len(template_examples[template_id]) < 5:
                template_examples[template_id].append(
                    {
                        "conversation_id": conv.get("conversation_id") or conv.get("id"),
                        "title": conv.get("title"),
                        "gizmo_type": conv.get("gizmo_type"),
                        "memory_scope": conv.get("memory_scope"),
                        "default_model_slug": conv.get("default_model_slug"),
                    }
                )

    return template_counts, template_examples


def main():
    root = find_workspace_root()
    raw_export_dir = root / "raw_export"

    zip_files = list(raw_export_dir.rglob("*chatgpt-*.zip"))
    if not zip_files:
        raise FileNotFoundError("Conversation ZIP file not found under raw_export.")

    zip_path = zip_files[0]
    print(f"Inspecting ZIP: {zip_path}")

    container_hits = defaultdict(list)

    with zipfile.ZipFile(zip_path, "r") as zf:
        template_counts, template_examples = collect_conversation_template_ids(zf)

        print("\nConversation template IDs found in conversations:")
        print(f"Unique template IDs: {len(template_counts)}")
        print(f"Total conversations with template ID: {sum(template_counts.values())}")

        for template_id, count in template_counts.most_common(30):
            print(f"\n### {template_id} ({count} conversations)")
            for ex in template_examples[template_id]:
                print(
                    f"  - {ex['conversation_id']} | "
                    f"{ex['title']} | "
                    f"gizmo_type={ex['gizmo_type']} | "
                    f"memory_scope={ex['memory_scope']} | "
                    f"model={ex['default_model_slug']}"
                )

        print("\nScanning structured files for container IDs / possible names...")

        infos = zf.infolist()

        for info in infos:
            filename = info.filename
            suffix = Path(filename).suffix.lower()

            # Skip the large conversations files here; they were handled above.
            if filename.startswith("conversations-") and filename.endswith(".json"):
                continue

            if suffix not in STRUCTURED_SUFFIXES:
                continue

            if suffix == ".json":
                inspect_json_file(zf, filename, container_hits)
            else:
                inspect_text_file(zf, info, container_hits)

    print("\nContainer ID hits outside conversations-*.json:")
    if not container_hits:
        print("No container IDs found outside conversations-*.json.")
    else:
        for container_id, hits in sorted(
            container_hits.items(),
            key=lambda item: (-len(item[1]), item[0])
        ):
            print(f"\n### {container_id}")
            print(f"Hits: {len(hits)}")

            for hit in hits[:10]:
                print(f"  File: {hit['file']}")
                print(f"  Path: {hit['path']}")

                if hit["nearby_name_fields"]:
                    print(f"  Nearby name-like fields: {short(hit['nearby_name_fields'])}")

                print(f"  Preview: {short(hit['value_preview'], max_len=700)}")

    print("\nDone.")


if __name__ == "__main__":
    main()