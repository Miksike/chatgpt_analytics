from pathlib import Path
import csv
from collections import Counter, defaultdict


INPUT_MANIFEST = "conversation_blocks_for_mode_discovery_manifest.csv"

OUT_CONTAINER_SUMMARY = "container_block_summary.csv"
OUT_STATUS_SUMMARY = "status_block_summary.csv"
OUT_MARKER_SUMMARY = "marker_summary.csv"
OUT_TEST_CANDIDATES = "mode_discovery_test_candidates.csv"
OUT_PROFILE = "conversation_blocks_profile.txt"


BOOL_FIELDS = [
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


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_bool(value) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_int(value, default=0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def read_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def calculate_signal_scores(row: dict) -> dict:
    """
    These are not final analytical classifications.
    They are only first-pass triage scores for choosing test cases.
    """
    peop_signal_score = 0
    friction_proxy_score = 0
    log_signal_score = 0

    if parse_bool(row.get("mentions_peop")):
        peop_signal_score += 4
    if parse_bool(row.get("mentions_canvas")):
        peop_signal_score += 3
    if parse_bool(row.get("mentions_context")):
        peop_signal_score += 2
    if parse_bool(row.get("mentions_new_chat")):
        peop_signal_score += 3
    if parse_bool(row.get("has_workmode_header")):
        peop_signal_score += 3
    if parse_bool(row.get("has_alm_marker")):
        peop_signal_score += 3
    if parse_bool(row.get("mentions_project")):
        peop_signal_score += 1
    if parse_bool(row.get("mentions_file")):
        peop_signal_score += 1

    if parse_bool(row.get("has_log_prefix_e")):
        log_signal_score += 2
    if parse_bool(row.get("has_log_prefix_a")):
        log_signal_score += 2
    if parse_bool(row.get("has_log_prefix_l")):
        log_signal_score += 2
    if parse_bool(row.get("has_log_prefix_n")):
        log_signal_score += 2

    title_and_excerpts = " ".join(
        [
            row.get("conversation_title", ""),
            row.get("first_user_excerpt", ""),
            row.get("last_user_excerpt", ""),
        ]
    ).lower()

    friction_terms = [
        "ei leia",
        "läks sassi",
        "kadus",
        "ei saa aru",
        "kordamine",
        "kontekst puudub",
        "uues vestluses",
        "raw on liiga raske",
        "token limit",
        "lõuendit ei tohi",
        "ära lõuendit muuda",
        "fail ei ole nähtav",
        "ei tööta",
        "vale",
        "segane",
    ]

    for term in friction_terms:
        if term in title_and_excerpts:
            friction_proxy_score += 1

    chars_total = parse_int(row.get("chars_total"))
    length_score = 0
    if chars_total >= 50000:
        length_score = 4
    elif chars_total >= 30000:
        length_score = 3
    elif chars_total >= 15000:
        length_score = 2
    elif chars_total >= 5000:
        length_score = 1

    case_candidate_score = (
        peop_signal_score
        + friction_proxy_score
        + log_signal_score
        + length_score
    )

    return {
        "peop_signal_score": peop_signal_score,
        "friction_proxy_score": friction_proxy_score,
        "log_signal_score": log_signal_score,
        "length_score": length_score,
        "case_candidate_score": case_candidate_score,
    }


def summarize_by_container(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)

    for row in rows:
        key = (
            row.get("container_id") or "",
            row.get("container_kind") or "none",
            row.get("container_label") or "",
            row.get("container_status") or "unknown",
        )
        grouped[key].append(row)

    summary_rows = []

    for (container_id, container_kind, container_label, container_status), items in grouped.items():
        block_count = len(items)
        conversation_ids = {r.get("conversation_id") for r in items}
        chars_total = sum(parse_int(r.get("chars_total")) for r in items)

        marker_counts = {
            field: sum(1 for r in items if parse_bool(r.get(field)))
            for field in BOOL_FIELDS
        }

        scored_items = [calculate_signal_scores(r) for r in items]

        summary_rows.append(
            {
                "container_id": container_id,
                "container_kind": container_kind,
                "container_label": container_label,
                "container_status": container_status,
                "block_count": block_count,
                "conversation_count": len(conversation_ids),
                "chars_total": chars_total,
                "avg_chars_per_block": round(chars_total / block_count, 1) if block_count else 0,
                "mentions_peop_blocks": marker_counts["mentions_peop"],
                "mentions_canvas_blocks": marker_counts["mentions_canvas"],
                "mentions_context_blocks": marker_counts["mentions_context"],
                "mentions_new_chat_blocks": marker_counts["mentions_new_chat"],
                "has_workmode_header_blocks": marker_counts["has_workmode_header"],
                "has_alm_marker_blocks": marker_counts["has_alm_marker"],
                "log_prefix_blocks": (
                    marker_counts["has_log_prefix_e"]
                    + marker_counts["has_log_prefix_a"]
                    + marker_counts["has_log_prefix_l"]
                    + marker_counts["has_log_prefix_n"]
                ),
                "max_case_candidate_score": max(
                    (s["case_candidate_score"] for s in scored_items),
                    default=0,
                ),
                "avg_case_candidate_score": round(
                    sum(s["case_candidate_score"] for s in scored_items) / block_count,
                    2,
                )
                if block_count
                else 0,
            }
        )

    return sorted(
        summary_rows,
        key=lambda r: (-parse_int(r["block_count"]), r["container_label"]),
    )


def summarize_by_status(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)

    for row in rows:
        key = (
            row.get("container_status") or "unknown",
            row.get("container_kind") or "none",
        )
        grouped[key].append(row)

    summary_rows = []

    for (container_status, container_kind), items in grouped.items():
        block_count = len(items)
        conversation_ids = {r.get("conversation_id") for r in items}
        chars_total = sum(parse_int(r.get("chars_total")) for r in items)

        summary_rows.append(
            {
                "container_status": container_status,
                "container_kind": container_kind,
                "block_count": block_count,
                "conversation_count": len(conversation_ids),
                "chars_total": chars_total,
                "avg_chars_per_block": round(chars_total / block_count, 1) if block_count else 0,
            }
        )

    return sorted(
        summary_rows,
        key=lambda r: (-parse_int(r["block_count"]), r["container_status"], r["container_kind"]),
    )


def summarize_markers(rows: list[dict]) -> list[dict]:
    total = len(rows)
    output = []

    for field in BOOL_FIELDS:
        count = sum(1 for row in rows if parse_bool(row.get(field)))
        output.append(
            {
                "marker": field,
                "block_count": count,
                "share_of_blocks": round(count / total, 4) if total else 0,
            }
        )

    return sorted(output, key=lambda r: -parse_int(r["block_count"]))


def build_test_candidates(rows: list[dict]) -> list[dict]:
    enriched = []

    for row in rows:
        scores = calculate_signal_scores(row)

        candidate_reason_parts = []

        if scores["peop_signal_score"] >= 6:
            candidate_reason_parts.append("strong PeOp/proto-workspace signal")
        if scores["log_signal_score"] >= 2:
            candidate_reason_parts.append("log/planning signal")
        if scores["friction_proxy_score"] >= 1:
            candidate_reason_parts.append("possible friction")
        if parse_bool(row.get("has_workmode_header")):
            candidate_reason_parts.append("explicit workmode header")
        if parse_bool(row.get("mentions_new_chat")):
            candidate_reason_parts.append("cross-chat continuity")
        if parse_bool(row.get("has_alm_marker")):
            candidate_reason_parts.append("canvas-control protocol")
        if scores["length_score"] >= 2:
            candidate_reason_parts.append("substantial conversation block")

        if not candidate_reason_parts:
            continue

        enriched_row = {
            "case_candidate_score": scores["case_candidate_score"],
            "peop_signal_score": scores["peop_signal_score"],
            "friction_proxy_score": scores["friction_proxy_score"],
            "log_signal_score": scores["log_signal_score"],
            "length_score": scores["length_score"],
            "candidate_reason": "; ".join(candidate_reason_parts),

            "block_id": row.get("block_id"),
            "conversation_id": row.get("conversation_id"),
            "conversation_title": row.get("conversation_title"),
            "conversation_create_time": row.get("conversation_create_time"),
            "conversation_update_time": row.get("conversation_update_time"),

            "container_id": row.get("container_id"),
            "container_kind": row.get("container_kind"),
            "container_label": row.get("container_label"),
            "container_status": row.get("container_status"),

            "block_index": row.get("block_index"),
            "block_count": row.get("block_count"),
            "is_complete_conversation": row.get("is_complete_conversation"),
            "message_count": row.get("message_count"),
            "user_messages": row.get("user_messages"),
            "assistant_messages": row.get("assistant_messages"),
            "chars_total": row.get("chars_total"),

            "first_user_excerpt": row.get("first_user_excerpt"),
            "last_user_excerpt": row.get("last_user_excerpt"),
        }

        for field in BOOL_FIELDS:
            enriched_row[field] = row.get(field)

        enriched.append(enriched_row)

    # Keep the candidate table usable: high-value first.
    enriched = sorted(
        enriched,
        key=lambda r: (
            -parse_int(r["case_candidate_score"]),
            r.get("container_label") or "",
            r.get("conversation_title") or "",
        ),
    )

    return enriched


def write_profile_text(path: Path, rows: list[dict], container_summary: list[dict], status_summary: list[dict], candidates: list[dict]):
    total_blocks = len(rows)
    total_conversations = len({r.get("conversation_id") for r in rows})
    split_blocks = sum(1 for r in rows if str(r.get("is_complete_conversation")).lower() == "false")

    container_status_counts = Counter(r.get("container_status") or "unknown" for r in rows)
    container_kind_counts = Counter(r.get("container_kind") or "none" for r in rows)

    with path.open("w", encoding="utf-8") as f:
        f.write("# Conversation blocks profile\n\n")

        f.write("## Overall\n\n")
        f.write(f"Blocks: {total_blocks}\n")
        f.write(f"Conversations: {total_conversations}\n")
        f.write(f"Blocks from split conversations: {split_blocks}\n")
        f.write(f"Candidate blocks: {len(candidates)}\n\n")

        f.write("## Container kind counts\n\n")
        for key, value in container_kind_counts.most_common():
            f.write(f"- {key}: {value}\n")

        f.write("\n## Container status counts\n\n")
        for key, value in container_status_counts.most_common():
            f.write(f"- {key}: {value}\n")

        f.write("\n## Top containers by block count\n\n")
        for item in container_summary[:20]:
            label = item["container_label"] or "NO_CONTAINER"
            f.write(
                f"- {label} | "
                f"kind={item['container_kind']} | "
                f"status={item['container_status']} | "
                f"blocks={item['block_count']} | "
                f"conversations={item['conversation_count']} | "
                f"max_case_score={item['max_case_candidate_score']}\n"
            )

        f.write("\n## Top test candidates\n\n")
        for item in candidates[:30]:
            f.write(
                f"- score={item['case_candidate_score']} | "
                f"{item['container_label'] or 'NO_CONTAINER'} | "
                f"{item['conversation_title']} | "
                f"{item['candidate_reason']} | "
                f"{item['block_id']}\n"
            )


def main():
    root = find_workspace_root()
    working_data_dir = root / "working_data"
    reports_dir = root / "reports"
    reports_dir.mkdir(exist_ok=True)

    manifest_path = working_data_dir / INPUT_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    rows = read_manifest(manifest_path)
    print(f"Loaded blocks from manifest: {len(rows)}")

    container_summary = summarize_by_container(rows)
    status_summary = summarize_by_status(rows)
    marker_summary = summarize_markers(rows)
    candidates = build_test_candidates(rows)

    container_summary_path = reports_dir / OUT_CONTAINER_SUMMARY
    status_summary_path = reports_dir / OUT_STATUS_SUMMARY
    marker_summary_path = reports_dir / OUT_MARKER_SUMMARY
    candidates_path = reports_dir / OUT_TEST_CANDIDATES
    profile_path = reports_dir / OUT_PROFILE

    write_csv(
        container_summary_path,
        container_summary,
        [
            "container_id",
            "container_kind",
            "container_label",
            "container_status",
            "block_count",
            "conversation_count",
            "chars_total",
            "avg_chars_per_block",
            "mentions_peop_blocks",
            "mentions_canvas_blocks",
            "mentions_context_blocks",
            "mentions_new_chat_blocks",
            "has_workmode_header_blocks",
            "has_alm_marker_blocks",
            "log_prefix_blocks",
            "max_case_candidate_score",
            "avg_case_candidate_score",
        ],
    )

    write_csv(
        status_summary_path,
        status_summary,
        [
            "container_status",
            "container_kind",
            "block_count",
            "conversation_count",
            "chars_total",
            "avg_chars_per_block",
        ],
    )

    write_csv(
        marker_summary_path,
        marker_summary,
        [
            "marker",
            "block_count",
            "share_of_blocks",
        ],
    )

    candidate_fieldnames = [
        "case_candidate_score",
        "peop_signal_score",
        "friction_proxy_score",
        "log_signal_score",
        "length_score",
        "candidate_reason",
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
        "first_user_excerpt",
        "last_user_excerpt",
    ] + BOOL_FIELDS

    write_csv(
        candidates_path,
        candidates,
        candidate_fieldnames,
    )

    write_profile_text(
        profile_path,
        rows,
        container_summary,
        status_summary,
        candidates,
    )

    print("\nDone.")
    print(f"Saved: {container_summary_path}")
    print(f"Saved: {status_summary_path}")
    print(f"Saved: {marker_summary_path}")
    print(f"Saved: {candidates_path}")
    print(f"Saved: {profile_path}")

    print("\nOverall:")
    print(f"Blocks: {len(rows)}")
    print(f"Conversations: {len({r.get('conversation_id') for r in rows})}")
    print(f"Candidate blocks: {len(candidates)}")

    print("\nTop containers:")
    for item in container_summary[:10]:
        print(
            f"- {item['container_label'] or 'NO_CONTAINER'} | "
            f"{item['container_status']} | "
            f"blocks={item['block_count']} | "
            f"conversations={item['conversation_count']} | "
            f"max_score={item['max_case_candidate_score']}"
        )

    print("\nTop candidates:")
    for item in candidates[:10]:
        print(
            f"- score={item['case_candidate_score']} | "
            f"{item['container_label'] or 'NO_CONTAINER'} | "
            f"{item['conversation_title']} | "
            f"{item['candidate_reason']}"
        )


if __name__ == "__main__":
    main()