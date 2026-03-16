from types import SimpleNamespace

from app.infrastructure.adapters.github.github_pull_request_publisher_adapter import (
    GitHubPullRequestPublisherAdapter,
)


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append((method, url, headers or {}, kwargs))
        return self._responses.pop(0)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):  # type: ignore[no-untyped-def]
        return self._payload

    def raise_for_status(self) -> None:
        return None


class TestGitHubPullRequestPublisherAdapter:
    def test_reuses_existing_open_pull_request(self) -> None:
        client = _FakeClient([
            _FakeResponse([
                {"number": 99, "html_url": "https://github.com/acme/refactor-agent/pull/99"}
            ])
        ])
        adapter = GitHubPullRequestPublisherAdapter("token", client=client)

        result = adapter.publish("acme/refactor-agent", "main", "ticket123_refactor", "title", "body")

        assert result.created is False
        assert result.number == 99

    def test_creates_pull_request_when_none_exists(self) -> None:
        client = _FakeClient([
            _FakeResponse([]),
            _FakeResponse({"number": 100, "html_url": "https://github.com/acme/refactor-agent/pull/100"}),
        ])
        adapter = GitHubPullRequestPublisherAdapter("token", client=client)

        result = adapter.publish("acme/refactor-agent", "main", "ticket123_refactor", "title", "body")

        assert result.created is True
        assert result.number == 100