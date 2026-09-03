import argparse
import json
from pathlib import Path

from app.common.logging import configure_logging
from app.config import get_settings
from app.demo import load_mock_events, run_demo
from app.prediction.label_builder import build_upgrade_labels
from app.rag.service import RAGService


def _print(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def command_demo() -> None:
    result = run_demo()
    public_result = {
        key: value
        for key, value in result.items()
        if key not in {"events", "visible_events", "business_context"}
    }
    _print(public_result)


def command_rag_demo() -> None:
    settings = get_settings()
    service = RAGService(settings.vector_index_path)
    path = settings.knowledge_dir / "mock_policy.md"
    count = service.index_file(path, approved=False)
    _print({"indexed_chunks": count, "results": service.search("证据失败后能否处置", top_k=2)})


def command_label_demo() -> None:
    events = load_mock_events()
    labels = build_upgrade_labels(events, supplier_ids=["S-MOCK-01"], max_week=12)
    _print([row for row in labels if row["upgrade_label"] == 1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Jiujiang multi-agent skeleton")
    parser.add_argument("command", choices=("demo", "rag-demo", "label-demo"), nargs="?", default="demo")
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    {"demo": command_demo, "rag-demo": command_rag_demo, "label-demo": command_label_demo}[args.command]()


if __name__ == "__main__":
    main()
