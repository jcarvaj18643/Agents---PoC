from typing import Any

import httpx

from app.application.ports.outbound.pull_request_publisher_port import (
    PullRequestPublisherPort,
)
from app.domain.value_objects.pull_request_publication import PullRequestPublication


class GitHubPullRequestPublisherAdapter(PullRequestPublisherPort):
    """Create or reuse an open GitHub pull request for a review branch."""

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
        base_branch: str,
        head_branch: str,
        title: str,
        body: str,
    ) -> PullRequestPublication:
        owner = repository.split("/", maxsplit=1)[0]
        existing_response = self._request(
            "GET",
            f"/repos/{repository}/pulls",
            params={"state": "open", "head": f"{owner}:{head_branch}"},
        )
        existing_items = existing_response.json()
        if isinstance(existing_items, list) and existing_items:
            existing = existing_items[0]
            return PullRequestPublication(
                number=int(existing["number"]),
                url=str(existing["html_url"]),
                head_branch=head_branch,
                base_branch=base_branch,
                created=False,
            )

        create_response = self._request(
            "POST",
            f"/repos/{repository}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
            },
        )
        created = create_response.json()
        return PullRequestPublication(
            number=int(created["number"]),
            url=str(created["html_url"]),
            head_branch=head_branch,
            base_branch=base_branch,
            created=True,
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