from pathlib import Path
from datetime import datetime
import csv
import json
import zipfile


MAX_BLOCK_CHARS = 50000
ROLES_TO_KEEP = {"user", "assistant"}


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def timestamp_to_iso(value):
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value)).isoformat()
    except Exception:
        return None


def safe_slug_text(value):
    if value in (None, "", [], {}):
        return ""
    return str(value).strip()


def load_container_registry(path: Path) -> dict:
    """
    Load reconstructed container registry.

    Expected key:
      container_id

    Useful optional fields:
      manual_label
      project_name
      container_kind
      manual_status
      manual_label_source
      manual_label_caveat
    """
    if not path.exists():
        print(f"WARNING: Container registry not found: {path}")
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    registry = {}

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        # Support either {"containers": [...]} or {"g-p-...": {...}}
        if isinstance(data.get("containers"), list):
            items = data["containers"]
        else:
            items = []
            for key, value in data.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("container_id", key)
                    items.append(item)
    else:
        raise ValueError("Container registry must be a JSON list or dict.")

    for item in items:
        container_id = item.get("container_id")
        if not container_id:
            continue
        registry[container_id] = item

    print(f"Loaded container registry entries: {len(registry)}")
    return registry


def infer_container_kind(container_id, gizmo_type, registry_item):
    if registry_item:
        kind = registry_item.get("container_kind")
        if kind:
            return kind

    if container_id and str(container_id).startswith("g-p-"):
        return "project"

    if gizmo_type == "gpt":
        return "gpt"

    if container_id and str(container_id).startswith("g-"):
        return "gpt"

    return "none"


def infer_container_label(container_id, registry_item):
    if not registry_item:
        return None

    for key in ["manual_label", "project_name", "container_label", "label", "name"]:
        value = registry_item.get(key)
        if value not in (None, "", [], {}):
            return value

    return None


def infer_container_status(container_id, registry_item, label):
    if registry_item:
        for key in ["manual_status", "status", "container_status"]:
            value = registry_item.get(key)
            if value not in (None, "", [], {}):
                return value

    if container_id and str(container_id).startswith("g-") and not str(container_id).startswith("g-p-"):
        return "gpt"

    if not label:
        return "unknown"

    label_lower = label.lower()

    if label.startswith("[A]") or label_lower.startswith("a "):
        return "archived"

    if label.startswith("[P]") or label_lower.startswith("p "):
        return "parked"

    if "tööruum" in label_lower:
        return "current"

    return "older"


def extract_text_from_message(message) -> str | None:
    if not message:
        return None

    content = message.get("content")
    if not content:
        return None

    parts = content.get("parts")

    if isinstance(parts, list):
        text_parts = []
        for part in parts:
            if isinstance(part, str):
                text_parts.append(part)
            elif part is not None:
                text_parts.append(json.dumps(part, ensure_ascii=False))
        text = "\n".join(text_parts).strip()
        return text if text else None

    text = content.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def get_linear_node_ids(mapping: dict, current_node: str | None) -> list[str]:
    """
    Reconstruct the visible/current conversation path by walking
    from current_node through parent links to root.

    This preserves the active branch, not all abandoned branches.
    """
    if not current_node:
        return []

    node_ids = []
    seen = set()
    node_id = current_node

    while node_id and node_id in mapping and node_id not in seen:
        node_ids.append(node_id)
        seen.add(node_id)
        node_id = mapping[node_id].get("parent")

    node_ids.reverse()
    return node_ids


def extract_messages_from_conversation(conv: dict) -> list[dict]:
    mapping = conv.get("mapping", {})
    current_node = conv.get("current_node")
    node_ids = get_linear_node_ids(mapping, current_node)

    messages = []
    message_no = 1

    for node_id in node_ids:
        node = mapping.get(node_id, {})
        message = node.get("message")

        if not message:
            continue

        role = message.get("author", {}).get("role")
        if role not in ROLES_TO_KEEP:
            continue

        text = extract_text_from_message(message)
        if not text:
            continue

        timestamp_raw = message.get("create_time")
        timestamp_iso = timestamp_to_iso(timestamp_raw)

        messages.append(
            {
                "message_no": message_no,
                "node_id": node_id,
                "role": role,
                "timestamp": timestamp_iso,
                "text": text,
                "text_chars": len(text),
            }
        )
        message_no += 1

    return messages


def format_message(msg: dict) -> str:
    timestamp = msg["timestamp"] or "NO_TIMESTAMP"
    role = msg["role"].upper()
    message_no = msg["message_no"]
    text = msg["text"]

    return f"[{message_no:04d}] [{timestamp}] {role}:\n{text}"


def split_messages_into_blocks(messages: list[dict], max_chars: int) -> list[list[dict]]:
    """
    Split only when needed for very long conversations.
    This is not mode segmentation.
    """
    blocks = []
    current = []
    current_chars = 0

    for msg in messages:
        formatted = format_message(msg)
        msg_chars = len(formatted) + 10

        if current and current_chars + msg_chars > max_chars:
            blocks.append(current)
            current = []
            current_chars = 0

        current.append(msg)
        current_chars += msg_chars

    if current:
        blocks.append(current)

    return blocks


def build_text_block(block_messages: list[dict]) -> str:
    return "\n\n---\n\n".join(format_message(msg) for msg in block_messages)


def detect_visible_markers(text: str) -> dict:
    t = text.lower()

    return {
        "mentions_peop": "peop" in t,
        "mentions_canvas": ("lõuend" in t) or ("canvas" in t),
        "mentions_context": "kontekst" in t or "context" in t,
        "mentions_project": "projekt" in t or "project" in t,
        "mentions_file": any(
            marker in t
            for marker in [
                ".txt",
                ".json",
                ".jsonl",
                ".csv",
                ".xlsx",
                ".docx",
                ".pdf",
                "fail",
                "file",
                "zip",
            ]
        ),
        "mentions_new_chat": (
            "uus vestlus" in t
            or "uude vestlusse" in t
            or "teise vestlusse" in t
            or "new chat" in t
        ),
        "has_workmode_header": "töörežiim:" in t,
        "has_alm_marker": "älm" in t or "ära lõuendit muuda" in t,
        "has_log_prefix_e": "\ne:" in t or t.startswith("e:"),
        "has_log_prefix_a": "\na:" in t or t.startswith("a:"),
        "has_log_prefix_l": "\nl:" in t or t.startswith("l:"),
        "has_log_prefix_n": "\nn:" in t or t.startswith("n:"),
    }


def main():
    root = find_workspace_root()
    raw_export_dir = root / "raw_export"
    working_data_dir = root / "working_data"
    working_data_dir.mkdir(exist_ok=True)

    registry_path = working_data_dir / "container_registry_final.json"

    out_jsonl = working_data_dir / "conversation_blocks_for_mode_discovery.jsonl"
    out_manifest = working_data_dir / "conversation_blocks_for_mode_discovery_manifest.csv"

    registry = load_container_registry(registry_path)

    zip_files = list(raw_export_dir.rglob("*chatgpt-*.zip"))
    if not zip_files:
        raise FileNotFoundError("Conversation ZIP file not found under raw_export.")

    zip_path = zip_files[0]
    print(f"Using ZIP: {zip_path}")

    records = []
    manifest_rows = []

    conversations_processed = 0
    conversations_with_messages = 0
    split_conversations = 0
    registry_hits = 0
    registry_misses = 0

    missing_container_ids = {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        json_files = sorted(
            name
            for name in zf.namelist()
            if name.startswith("conversations-") and name.endswith(".json")
        )

        if not json_files:
            raise FileNotFoundError("No conversations-*.json files found in ZIP.")

        for json_file in json_files:
            print(f"Processing {json_file}")

            with zf.open(json_file) as f:
                conversations = json.load(f)

            for conv in conversations:
                conversations_processed += 1

                conversation_id = conv.get("conversation_id") or conv.get("id")
                title = safe_slug_text(conv.get("title"))
                create_time = timestamp_to_iso(conv.get("create_time"))
                update_time = timestamp_to_iso(conv.get("update_time"))

                conversation_template_id = conv.get("conversation_template_id")
                gizmo_type = conv.get("gizmo_type")
                memory_scope = conv.get("memory_scope")
                default_model_slug = conv.get("default_model_slug")
                is_archived = conv.get("is_archived")
                is_do_not_remember = conv.get("is_do_not_remember")

                container_id = conversation_template_id
                registry_item = registry.get(container_id) if container_id else None

                if container_id:
                    if registry_item:
                        registry_hits += 1
                    else:
                        registry_misses += 1
                        missing_container_ids[container_id] = missing_container_ids.get(container_id, 0) + 1

                container_kind = infer_container_kind(container_id, gizmo_type, registry_item)
                container_label = infer_container_label(container_id, registry_item)
                container_status = infer_container_status(container_id, registry_item, container_label)

                messages = extract_messages_from_conversation(conv)

                if not messages:
                    continue

                conversations_with_messages += 1

                blocks = split_messages_into_blocks(messages, MAX_BLOCK_CHARS)
                block_count = len(blocks)

                if block_count > 1:
                    split_conversations += 1

                for idx, block_messages in enumerate(blocks, start=1):
                    text_block = build_text_block(block_messages)
                    markers = detect_visible_markers(text_block)

                    block_id = f"{conversation_id}::block_{idx:03d}"

                    user_messages = sum(1 for m in block_messages if m["role"] == "user")
                    assistant_messages = sum(1 for m in block_messages if m["role"] == "assistant")
                    user_chars = sum(m["text_chars"] for m in block_messages if m["role"] == "user")
                    assistant_chars = sum(m["text_chars"] for m in block_messages if m["role"] == "assistant")

                    first_user_text = next(
                        (m["text"] for m in block_messages if m["role"] == "user"),
                        "",
                    )
                    last_user_text = next(
                        (m["text"] for m in reversed(block_messages) if m["role"] == "user"),
                        "",
                    )

                    record = {
                        "block_id": block_id,
                        "conversation_id": conversation_id,
                        "conversation_title": title,
                        "conversation_create_time": create_time,
                        "conversation_update_time": update_time,

                        "container_id": container_id,
                        "container_kind": container_kind,
                        "container_label": container_label,
                        "container_status": container_status,

                        "container_registry": registry_item or None,
                        "conversation_template_id": conversation_template_id,
                        "gizmo_type": gizmo_type,
                        "memory_scope": memory_scope,
                        "default_model_slug": default_model_slug,
                        "is_archived": is_archived,
                        "is_do_not_remember": is_do_not_remember,

                        "block_index": idx,
                        "block_count": block_count,
                        "is_complete_conversation": block_count == 1,
                        "start_message_no": block_messages[0]["message_no"],
                        "end_message_no": block_messages[-1]["message_no"],
                        "message_count": len(block_messages),
                        "user_messages": user_messages,
                        "assistant_messages": assistant_messages,
                        "chars_total": len(text_block),
                        "chars_user": user_chars,
                        "chars_assistant": assistant_chars,

                        "first_user_excerpt": first_user_text[:400].replace("\n", " "),
                        "last_user_excerpt": last_user_text[:400].replace("\n", " "),

                        "visible_markers": markers,
                        "text_block": text_block,
                    }

                    records.append(record)

                    manifest_row = {
                        "block_id": block_id,
                        "conversation_id": conversation_id,
                        "conversation_title": title,
                        "conversation_create_time": create_time,
                        "conversation_update_time": update_time,

                        "container_id": container_id,
                        "container_kind": container_kind,
                        "container_label": container_label,
                        "container_status": container_status,

                        "conversation_template_id": conversation_template_id,
                        "gizmo_type": gizmo_type,
                        "memory_scope": memory_scope,
                        "default_model_slug": default_model_slug,

                        "block_index": idx,
                        "block_count": block_count,
                        "is_complete_conversation": block_count == 1,
                        "start_message_no": block_messages[0]["message_no"],
                        "end_message_no": block_messages[-1]["message_no"],
                        "message_count": len(block_messages),
                        "user_messages": user_messages,
                        "assistant_messages": assistant_messages,
                        "chars_total": len(text_block),
                        "chars_user": user_chars,
                        "chars_assistant": assistant_chars,

                        "first_user_excerpt": first_user_text[:300].replace("\n", " "),
                        "last_user_excerpt": last_user_text[:300].replace("\n", " "),
                    }

                    manifest_row.update(markers)
                    manifest_rows.append(manifest_row)

    with out_jsonl.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    fieldnames = [
        "block_id",
        "conversation_id",
        "conversation_title",
        "conversation_create_time",
        "conversation_update_time",
        "container_id",
        "container_kind",
        "container_label",
        "container_status",
        "conversation_template_id",
        "gizmo_type",
        "memory_scope",
        "default_model_slug",
        "block_index",
        "block_count",
        "is_complete_conversation",
        "start_message_no",
        "end_message_no",
        "message_count",
        "user_messages",
        "assistant_messages",
        "chars_total",
        "chars_user",
        "chars_assistant",
        "first_user_excerpt",
        "last_user_excerpt",
        "mentions_peop",
        "mentions_canvas",
        "mentions_context",
        "mentions_project",
        "mentions_file",
        "mentions_new_chat",
        "has_workmode_header",
        "has_alm_marker",
        "has_log_prefix_e",
        "has_log_prefix_a",
        "has_log_prefix_l",
        "has_log_prefix_n",
    ]

    with out_manifest.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    print("\nDone.")
    print(f"Conversations processed: {conversations_processed}")
    print(f"Conversations with messages: {conversations_with_messages}")
    print(f"Conversation blocks written: {len(records)}")
    print(f"Split conversations: {split_conversations}")
    print(f"Max block chars: {MAX_BLOCK_CHARS}")
    print(f"Registry hits: {registry_hits}")
    print(f"Registry misses: {registry_misses}")

    if missing_container_ids:
        print("\nMissing container IDs:")
        for container_id, count in sorted(missing_container_ids.items(), key=lambda x: (-x[1], x[0])):
            print(f" - {container_id}: {count}")

    print(f"\nSaved JSONL: {out_jsonl}")
    print(f"Saved manifest: {out_manifest}")

    print("\nSample:")
    if records:
        sample = records[0]
        print(f"block_id: {sample['block_id']}")
        print(f"title: {sample['conversation_title']}")
        print(f"container: {sample['container_label']} ({sample['container_status']})")
        print(f"message_count: {sample['message_count']}")
        print(f"chars_total: {sample['chars_total']}")
        print(sample["text_block"][:1500])


if __name__ == "__main__":
    main()