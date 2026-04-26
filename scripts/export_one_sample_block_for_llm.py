from pathlib import Path
import json


# Muuda seda numbrit, kui tahad teist sample-plokki eksportida.
# Praeguses käsitsi valimis:
# 1-3 = 2026-N11 plokid
# 4 = Päkk ja mehhaanika
# 5 = Projektide parandused eksperdi järgi
# 6 = OneDrive konto vahetamine
# 7 = Vastuskiri pinnase olukorrast
# 8 = Elektriauto valiku juhend
SAMPLE_NO = 6


DISCOVERY_INSTRUCTION = """Töörežiim: PeOp mode-discovery test v2

Kontekst:
Allpool on üks ChatGPT kasutuse plokk minu ajaloolisest vestluskorpusest.
See EI pruugi olla terve vestlus, vaid võib olla pikema vestluse üks tehniline plokk.

Eesmärk:
Ära klassifitseeri etteantud taksonoomiasse.
Kirjelda, mis selles plokis tegelikult toimub.
Mode’id peavad tekkima vaatlusest, mitte etteantud kategooriate järgi.

Oluline:
- PeOp-i nime esinemine EI ole PeOp-signaali eeltingimus.
- PeOp-signaal tähendab kasutusmustrit: tööruum, konteksti taastamine, failide/tööriistade sidumine, fookuse hoidmine, otsustamine, töövoo juhtimine, lõuendi või vestluse kasutamine operatiivse kihina.
- Ära üleprojitseeri PeOp-i. Kui signaal on nõrk, märgi see nõrgaks.
- Erista kasutaja öeldut ja assistendi öeldut.
- Evidence excerpt peab olema lühike otsene väljavõte ploki tekstist.
- Märgi iga evidence_excerpt juurde evidence_source: user või assistant.
- Kasuta JSON boolean väärtusi true/false, mitte stringe "true"/"false".
- Tagasta ainult JSON. Ära lisa JSON-i ümber markdown plokki.

Analüüsi:
1. mida kasutaja üritab teha;
2. mis on töö objekt;
3. milliseid kasutusviise või töörežiime võib plokis näha;
4. millised proto-PeOp signaalid paistavad;
5. kui tugevad need proto-PeOp signaalid on;
6. millised kasutusraskused või hõõrdumised paistavad;
7. kas see plokk sobib hilisemaks case study’ks.
"""


JSON_SCHEMA_HINT = {
    "block_id": "string",
    "conversation_title": "string",
    "container_label": "string or null",
    "session_summary": {
        "one_sentence": "string",
        "what_user_is_trying_to_do": "string",
        "main_object_of_work": "string",
        "practical_outcome": "string"
    },
    "episodes": [
        {
            "episode_id": 1,
            "user_activity": "string",
            "assistant_role": "string",
            "object_of_attention": "string",
            "output_or_artifact": "string",
            "candidate_mode_description": "string",
            "evidence": {
                "evidence_excerpt": "short direct quote from the block",
                "evidence_source": "user|assistant"
            }
        }
    ],
    "candidate_modes": [
        {
            "mode_name_candidate": "string",
            "mode_description": "string",
            "why_this_is_a_mode": "string",
            "confidence": "low|medium|high",
            "evidence": {
                "evidence_excerpt": "short direct quote from the block",
                "evidence_source": "user|assistant"
            }
        }
    ],
    "proto_peop_signals": {
        "overall_signal_strength": "none|weak|medium|strong",
        "signals": [
            {
                "signal_type": "topic_as_workspace|context_restoration|focus_management|canvas_or_control_view|file_or_tool_binding|cross_session_continuity|manual_operating_protocol|ai_workflow_reflection|digital_workspace_boundary|decision_support|other",
                "present": "boolean true/false",
                "strength": "none|weak|medium|strong",
                "description": "string",
                "evidence": {
                    "evidence_excerpt": "short direct quote from the block",
                    "evidence_source": "user|assistant"
                }
            }
        ],
        "notes": "string"
    },
    "frictions": [
        {
            "friction_type": "context_loss|ui_limitation|tool_limitation|file_visibility|canvas_control|mode_confusion|output_misalignment|memory_uncertainty|token_limit|workflow_overhead|digital_workspace_boundary|other",
            "description": "string",
            "severity": "low|medium|high",
            "is_explicitly_stated_by_user": "boolean true/false",
            "evidence": {
                "evidence_excerpt": "short direct quote from the block",
                "evidence_source": "user|assistant"
            }
        }
    ],
    "artifacts_and_work_products": [
        {
            "artifact_type": "canvas|prompt|document|code|table|plan|summary|log|decision|schema|configuration|other",
            "description": "string"
        }
    ],
    "continuity": {
        "depends_on_previous_context": "boolean true/false",
        "creates_context_for_future_session": "boolean true/false",
        "mentions_transfer_to_another_chat": "boolean true/false",
        "mentions_returning_later": "boolean true/false",
        "notes": "string",
        "evidence": [
            {
                "evidence_excerpt": "short direct quote from the block",
                "evidence_source": "user|assistant"
            }
        ]
    },
    "research_value": {
        "use_for_timeline": "boolean true/false",
        "use_for_mode_discovery": "boolean true/false",
        "use_for_proto_peop_analysis": "boolean true/false",
        "use_for_friction_analysis": "boolean true/false",
        "case_study_candidate": "boolean true/false",
        "case_study_strength": "low|medium|high",
        "reason": "string"
    }
}


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


def main():
    root = find_workspace_root()
    working_data_dir = root / "working_data"

    input_path = working_data_dir / "manual_mode_discovery_sample.jsonl"

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    records = load_jsonl(input_path)

    matches = [r for r in records if int(r.get("sample_no", -1)) == SAMPLE_NO]

    if not matches:
        print("Available samples:")
        for r in records:
            print(
                f"- sample_no={r.get('sample_no')} | "
                f"{r.get('conversation_title')} | "
                f"{r.get('block_id')}"
            )
        raise SystemExit(f"Sample no {SAMPLE_NO} not found.")

    record = matches[0]

    output_path = working_data_dir / f"llm_test_input_sample_{SAMPLE_NO:02d}_v2.txt"

    metadata = {
        "sample_no": record.get("sample_no"),
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
        "message_count": record.get("message_count"),
        "chars_total": record.get("chars_total"),
        "sample_reason": record.get("sample_reason"),
    }

    text = (
        DISCOVERY_INSTRUCTION
        + "\n\n"
        + "JSON väljundi soovituslik skeem:\n"
        + json.dumps(JSON_SCHEMA_HINT, ensure_ascii=False, indent=2)
        + "\n\n"
        + "PLOKI METAANDMED:\n"
        + json.dumps(metadata, ensure_ascii=False, indent=2)
        + "\n\n"
        + "PLOKI TEKST:\n"
        + record.get("text_block", "")
        + "\n"
    )

    output_path.write_text(text, encoding="utf-8")

    print("\nDone.")
    print(f"Sample no: {SAMPLE_NO}")
    print(f"Title: {record.get('conversation_title')}")
    print(f"Block ID: {record.get('block_id')}")
    print(f"Container: {record.get('container_label') or 'NO_CONTAINER'}")
    print(f"Chars in block: {record.get('chars_total')}")
    print(f"Saved: {output_path}")

    print("\nPreview:")
    print(text[:2000])


if __name__ == "__main__":
    main()