import argparse
import json
import sys
from pathlib import Path

from app.common.logging import configure_logging
from app.config import get_settings
from app.demo import load_mock_events, run_demo, run_real_data_demo
from app.prediction.label_builder import build_upgrade_labels
from app.rag.service import RAGService


def _print(payload) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
    count = service.rebuild([(path, True)])
    _print(
        {
            "indexed_chunks": count,
            "mode": "APPROVED_SIMULATION_ONLY",
            "results": service.search("证据失败后能否处置", top_k=2, approved_only=True),
        }
    )


def command_label_demo() -> None:
    events = load_mock_events()
    labels = build_upgrade_labels(events, supplier_ids=["S-MOCK-01"], max_week=12)
    _print([row for row in labels if row["upgrade_label"] == 1])


def command_train() -> None:
    from app.prediction.training import train_all

    settings = get_settings()
    _print(train_all(source_dir=settings.source_data_dir))


def command_rollback_model() -> None:
    from app.prediction.training import rollback_latest

    _print(rollback_latest())


def command_real_data_demo() -> None:
    settings = get_settings()
    result = run_real_data_demo(source_dir=settings.source_data_dir)
    public_result = {
        key: value
        for key, value in result.items()
        if key not in {"events", "visible_events", "business_context", "model_features"}
    }
    _print(public_result)


def command_real_data_demo_live() -> None:
    settings = get_settings()
    result = run_real_data_demo(source_dir=settings.source_data_dir, enable_live_llm=True)
    public_result = {
        key: value
        for key, value in result.items()
        if key not in {"events", "visible_events", "business_context", "model_features", "policy_context"}
    }
    _print(public_result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jiujiang multi-agent skeleton")
    parser.add_argument(
        "command",
        choices=(
            "demo",
            "rag-demo",
            "label-demo",
            "train",
            "rollback-model",
            "real-data-demo",
            "real-data-demo-live",
        ),
        nargs="?",
        default="demo",
    )
    args = parser.parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    {
        "demo": command_demo,
        "rag-demo": command_rag_demo,
        "label-demo": command_label_demo,
        "train": command_train,
        "rollback-model": command_rollback_model,
        "real-data-demo": command_real_data_demo,
        "real-data-demo-live": command_real_data_demo_live,
    }[args.command]()


if __name__ == "__main__":
    main()
