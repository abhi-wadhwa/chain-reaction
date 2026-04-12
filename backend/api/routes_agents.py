from fastapi import APIRouter
from agents import AGENT_REGISTRY

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/types")
def get_agent_types():
    """Return available agent types with their configurable parameter schemas."""
    result = []
    for key, cls in AGENT_REGISTRY.items():
        instance = cls()
        config = instance.get_config()
        result.append({"type": key, **config})
    return result


@router.post("/validate")
def validate_agent_config(body: dict):
    """Validate an agent configuration."""
    agent_type = body.get("type")
    params = body.get("params", {})

    if agent_type not in AGENT_REGISTRY:
        return {"valid": False, "error": f"Unknown agent type: {agent_type}"}

    try:
        cls = AGENT_REGISTRY[agent_type]
        cls(**params)
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}
