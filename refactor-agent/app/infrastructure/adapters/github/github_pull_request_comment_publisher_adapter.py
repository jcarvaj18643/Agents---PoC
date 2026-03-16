from typing import Any

import httpx

from app.application.ports.outbound.pull_request_comment_publisher_port import (
    PullRequestCommentPublisherPort,
)
from app.domain.value_objects.pull_request_comment_publication import (
    PullRequestCommentPublication,
)

_COMMENT_MARKER = "<!-- engineering-governance-agent:summary -->"


class GitHubPullRequestCommentPublisherAdapter(PullRequestCommentPublisherPort):
    """Publish or update an idempotent summary comment on a GitHub pull request."""

    def __init__(
        self,
        github_token: str,
        api_base_url: str = "https://api.github.com",
        client: Any | None = None,
    ) -> None:
        self._github_token = github_token
        self._api_base_url = api_base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=30.0)

    def publish(
        self,
        repository: str,
        pull_request_number: int,
        body: str,
    ) -> PullRequestCommentPublication:
        comments_response = self._request(
            "GET",
            f"/repos/{repository}/issues/{pull_request_number}/comments",
        )
        comments = comments_response.json()
        if isinstance(comments, list):
            for item in comments:
                if isinstance(item, dict) and _COMMENT_MARKER in str(item.get("body", "")):
                    comment_id = int(item["id"])
                    update_response = self._request(
                        "PATCH",
                        f"/repos/{repository}/issues/comments/{comment_id}",
                        json={"body": body},
                    )
                    updated = update_response.json()
                    return PullRequestCommentPublication(
                        comment_id=comment_id,
                        url=str(updated["html_url"]),
                        updated=True,
                    )

        create_response = self._request(
            "POST",
            f"/repos/{repository}/issues/{pull_request_number}/comments",
            json={"body": body},
        )
        created = create_response.json()
        return PullRequestCommentPublication(
            comment_id=int(created["id"]),
            url=str(created["html_url"]),
            updated=False,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self._client.request(
            method,
            f"{self._api_base_url}{path}",
            headers={
                "Authorization": f"Bearer {self._github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            **kwargs,
        )
        response.raise_for_status()
        return response