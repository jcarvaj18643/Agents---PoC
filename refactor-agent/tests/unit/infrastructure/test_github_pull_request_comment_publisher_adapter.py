from app.infrastructure.adapters.github.github_pull_request_comment_publisher_adapter import (
    GitHubPullRequestCommentPublisherAdapter,
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


class TestGitHubPullRequestCommentPublisherAdapter:
    def test_updates_existing_marker_comment(self) -> None:
        client = _FakeClient([
            _FakeResponse([
                {
                    "id": 1234,
                    "body": "<!-- engineering-governance-agent:summary --> old",
                    "html_url": "https://github.com/acme/refactor-agent/pull/99#issuecomment-1234",
                }
            ]),
            _FakeResponse({
                "id": 1234,
                "html_url": "https://github.com/acme/refactor-agent/pull/99#issuecomment-1234",
            }),
        ])
        adapter = GitHubPullRequestCommentPublisherAdapter("token", client=client)

        result = adapter.publish("acme/refactor-agent", 99, "<!-- engineering-governance-agent:summary --> new")

        assert result.updated is True
        assert result.comment_id == 1234

    def test_creates_comment_when_no_marker_exists(self) -> None:
        client = _FakeClient([
            _FakeResponse([]),
            _FakeResponse({
                "id": 1235,
                "html_url": "https://github.com/acme/refactor-agent/pull/99#issuecomment-1235",
            }),
        ])
        adapter = GitHubPullRequestCommentPublisherAdapter("token", client=client)

        result = adapter.publish("acme/refactor-agent", 99, "<!-- engineering-governance-agent:summary --> new")

        assert result.updated is False
        assert result.comment_id == 1235