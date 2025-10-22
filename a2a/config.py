"""Typed helpers for accessing A2A configuration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from scripts.common import load_a2a_config


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    url: str
    capabilities: Mapping[str, bool]
    skills: Mapping[str, Mapping[str, str]]


class A2AConfig:
    def __init__(self) -> None:
        raw = load_a2a_config()
        self._agents: Dict[str, AgentDefinition] = {}
        for role, info in raw.get("agents", {}).items():
            if not isinstance(info, dict):
                continue
            url = str(info.get("url", "")).strip()
            if not url:
                continue
            capabilities = info.get("capabilities") if isinstance(info.get("capabilities"), dict) else {}
            skills = info.get("skills") if isinstance(info.get("skills"), dict) else {}
            self._agents[role] = AgentDefinition(
                name=role,
                url=url,
                capabilities=capabilities,
                skills=skills,
            )
        auth = raw.get("authentication", {})
        self.authentication_mode = str(auth.get("mode", "none")).lower()

    def agent(self, role: str) -> AgentDefinition:
        try:
            return self._agents[role]
        except KeyError as exc:
            raise KeyError(f"A2A agent not configured for role '{role}'") from exc

    def agents(self) -> Mapping[str, AgentDefinition]:
        return self._agents


def get_agent_url(role: str) -> str:
    return A2AConfig().agent(role).url
