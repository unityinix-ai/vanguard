"""Model routing configuration for Aurora.

Maps task types to configured LLM providers with fallback support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelProvider:
    name: str
    endpoint: str
    api_key: str = ""
    model: str = ""
    enabled: bool = True


@dataclass
class RouteRule:
    task_type: str
    provider: str
    fallback: str | None = None


class ReverseProxyConfiguration:
    """Configures reverse proxy routing for Caddy-managed WebSocket connections."""

    def __init__(self) -> None:
        self._routes: dict[str, str] = {}
        self._ws_paths: dict[str, str] = {}

    def add_route(self, path: str, backend: str) -> None:
        self._routes[path] = backend

    def add_ws_path(self, path: str, backend: str) -> None:
        self._ws_paths[path] = backend

    def get_route(self, path: str) -> str | None:
        return self._routes.get(path)

    def get_ws_backend(self, path: str) -> str | None:
        return self._ws_paths.get(path)

    def routes(self) -> dict[str, str]:
        return dict(self._routes)

    def ws_paths(self) -> dict[str, str]:
        return dict(self._ws_paths)


class ModelRouter:
    """Routes execution requests to configured model providers.

    Falls back to secondary providers if the primary is unavailable.
    """

    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self._rules: list[RouteRule] = []
        self.proxy = ReverseProxyConfiguration()

    def register_provider(self, provider: ModelProvider) -> None:
        self._providers[provider.name] = provider

    def add_rule(self, rule: RouteRule) -> None:
        self._rules.append(rule)

    def resolve(self, task_type: str) -> ModelProvider | None:
        """Resolve a task type to a provider, with fallback."""
        for rule in self._rules:
            if rule.task_type == task_type:
                provider = self._providers.get(rule.provider)
                if provider and provider.enabled:
                    return provider
                if rule.fallback:
                    fallback = self._providers.get(rule.fallback)
                    if fallback and fallback.enabled:
                        return fallback
        return None

    def get_provider(self, name: str) -> ModelProvider | None:
        return self._providers.get(name)

    def list_providers(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def list_rules(self) -> list[RouteRule]:
        return list(self._rules)


def create_default_router() -> ModelRouter:
    """Create a router with sensible defaults for local development."""
    router = ModelRouter()

    router.register_provider(
        ModelProvider(
            name="local",
            endpoint="ws://localhost:8001/ws",
            model="mock",
        )
    )

    router.add_rule(RouteRule(task_type="llm_completion", provider="local"))
    router.add_rule(RouteRule(task_type="voice_command", provider="local"))
    router.add_rule(RouteRule(task_type="default", provider="local"))

    router.proxy.add_route("/api", "gedo:8000")
    router.proxy.add_ws_path("/ws", "localhost:8001")

    return router
