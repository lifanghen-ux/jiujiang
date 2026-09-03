from datetime import datetime, timezone


def trace(agent_name: str, status: str, *, detail: str = "") -> list[dict]:
    return [
        {
            "agent_name": agent_name,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]

