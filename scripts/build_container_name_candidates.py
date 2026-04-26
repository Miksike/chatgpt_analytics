from pathlib import Path
from datetime import datetime
import json
import re
import zipfile
from collections import defaultdict, Counter


TOP_SAMPLE_TITLES = 12


def find_workspace_root() -> Path:
    return Path(__file__).resolve().parent.parent


def timestamp_to_iso(value):
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value)).isoformat()
    except Exception:
        return None


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return str(title).strip()


def make_auto_label_candidate(titles: list[str]) -> str:
    """
    Heuristic guess based on conversation titles.
    This is intentionally conservative and editable by the user.
    """
    joined = " | ".join(titles).lower()

    rules = [
        (
            ["2026-n", "nädal", "ajaplaneer", "sõiduplaan", "tegevuste planeerimine"],
            "Ajaplaneerimise tööruum",
        ),
        (
            ["liigutamise", "füüsilise", "treening", "koormus"],
            "Liigutamise tööruum",
        ),
        (
            ["enesetunde", "vererõhu", "tervise", "haiguse", "gripp"],
            "Enesetunde tööruum",
        ),
        (
            ["raamatupid", "rmtp", "aastaaruann", "bilans", "firma olukorra"],
            "RMTP tööruum",
        ),
        (
            ["päikese", "solax", "inverter", "energia", "elektritoot"],
            "Päikesepaneelide automaatjuhtimise tööruum",
        ),
        (
            ["geotehniline", "kutse", "kutsestandard", "ehitusgeoloog", "kutsetasem"],
            "Kutse standardi tööruum",
        ),
        (
            ["kiilvai", "vaia", "vaiad"],
            "Kiilvaia tööruum",
        ),
        (
            ["egü"],
            "EGÜ tööruum",
        ),
        (
            ["hinnapakk", "pakkumine"],
            "Hinnapakkumiste tööruum",
        ),
        (
            ["insenerarvutus", "arvutus", "raudbetoon", "maple", "power query", "excel vba"],
            "Insenerarvutuste tööruum",
        ),
        (
            ["keele", "läti keel", "tõlgi", "tõlkimine"],
            "Keele õppimise tööruum",
        ),
        (
            ["peop", "kasutusrežiim", "mode", "töörežiim"],
            "PeOp tööruum",
        ),
        (
            ["ehituse info", "infosüsteem", "failide", "andmete analüüs", "info haldamine"],
            "Kurmik arenduse tööruum",
        ),
        (
            ["objekti", "tugisein", "kai", "seletuskiri", "tiitelleht", "parandused projekti"],
            "Objekti juhtimise tööruum",
        ),
        (
            ["leidut", "poldiga", "kiilu", "palgi", "raud-õhk", "ferrovedelik"],
            "Leidutamise tööruum",
        ),
    ]

    for keywords, label in rules:
        if any(keyword in joined for keyword in keywords):
            return label

    # Fallback: try to produce a readable label from common title words.
    words = []
    for title in titles[:5]:
        for word in re.findall(r"[A-Za-zÕÄÖÜŠŽõäöüšž0-9\-]+", title):
            word_lower = word.lower()
            if len(word_lower) < 4:
                continue
            if word_lower in {
                "kuidas", "kas", "mis", "miks", "ning", "jaoks", "kohta",
                "selgitus", "analüüs", "koostamine", "täpsustamine",
            }:
                continue
            words.append(word)

    if not words:
        return ""

    common = Counter(words).most_common(3)
    return " / ".join(word for word, _ in common)


def main():
    root = find_workspace_root()
    raw_export_dir = root / "raw_export"
    working_data_dir = root / "working_data"
    working_data_dir.mkdir(exist_ok=True)

    out_path = working_data_dir / "container_name_candidates.json"

    zip_files = list(raw_export_dir.rglob("*chatgpt-*.zip"))
    if not zip_files:
        raise FileNotFoundError("Conversation ZIP file not found under raw_export.")

    zip_path = zip_files[0]

    containers = {}

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
                container_id = conv.get("conversation_template_id")
                if container_id in (None, "", [], {}):
                    continue

                conversation_id = conv.get("conversation_id") or conv.get("id")
                title = normalize_title(conv.get("title"))
                create_time = timestamp_to_iso(conv.get("create_time"))
                update_time = timestamp_to_iso(conv.get("update_time"))
                gizmo_type = conv.get("gizmo_type")
                memory_scope = conv.get("memory_scope")
                model = conv.get("default_model_slug")

                if container_id not in containers:
                    containers[container_id] = {
                        "container_id": container_id,
                        "container_type": gizmo_type,
                        "memory_scope_values": Counter(),
                        "model_values": Counter(),
                        "conversation_count": 0,
                        "first_time": create_time,
                        "last_time": update_time or create_time,
                        "sample_titles": [],
                        "sample_conversations": [],
                    }

                c = containers[container_id]
                c["conversation_count"] += 1

                if memory_scope:
                    c["memory_scope_values"][memory_scope] += 1
                if model:
                    c["model_values"][model] += 1

                if create_time and (c["first_time"] is None or create_time < c["first_time"]):
                    c["first_time"] = create_time

                candidate_last = update_time or create_time
                if candidate_last and (c["last_time"] is None or candidate_last > c["last_time"]):
                    c["last_time"] = candidate_last

                if title and title not in c["sample_titles"]:
                    if len(c["sample_titles"]) < TOP_SAMPLE_TITLES:
                        c["sample_titles"].append(title)

                if len(c["sample_conversations"]) < TOP_SAMPLE_TITLES:
                    c["sample_conversations"].append(
                        {
                            "conversation_id": conversation_id,
                            "title": title,
                            "create_time": create_time,
                            "update_time": update_time,
                            "model": model,
                        }
                    )

    output = []

    for container_id, c in containers.items():
        sample_titles = c["sample_titles"]
        auto_label = make_auto_label_candidate(sample_titles)

        output.append(
            {
                "container_id": container_id,
                "container_type": c["container_type"],
                "conversation_count": c["conversation_count"],
                "first_time": c["first_time"],
                "last_time": c["last_time"],
                "memory_scope_values": dict(c["memory_scope_values"]),
                "model_values": dict(c["model_values"]),
                "sample_titles": sample_titles,
                "sample_conversations": c["sample_conversations"],
                "auto_label_candidate": auto_label,
                "manual_label": "",
                "manual_status": "",
                "manual_notes": "",
            }
        )

    output = sorted(
        output,
        key=lambda x: (-x["conversation_count"], x["container_id"])
    )

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\nDone.")
    print(f"Containers: {len(output)}")
    print(f"Saved: {out_path}")

    print("\nTop candidates:")
    for item in output[:15]:
        print(
            f"- {item['container_id']} | "
            f"{item['conversation_count']} conversations | "
            f"auto: {item['auto_label_candidate']}"
        )
        print(f"  sample: {' | '.join(item['sample_titles'][:5])}")


if __name__ == "__main__":
    main()