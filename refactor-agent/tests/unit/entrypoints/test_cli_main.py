"""Unit tests for the CLI argument parsing."""

import sys

from app.entrypoints.cli.main import _parse_args


class TestCliArgumentParsing:
    def test_defaults_to_dry_run(self, monkeypatch) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "main",
                "--head-ref",
                "HEAD",
            ],
        )

        args = _parse_args()

        assert args.dry_run is True

    def test_allows_disabling_dry_run(self, monkeypatch) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "main",
                "--head-ref",
                "HEAD",
                "--no-dry-run",
            ],
        )

        args = _parse_args()

        assert args.dry_run is False

    def test_allows_enabling_apply_refactors(self, monkeypatch) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "main",
                "--head-ref",
                "HEAD",
                "--apply-refactors",
            ],
        )

        args = _parse_args()

        assert args.apply_refactors is True

    def test_allows_configuring_review_branch_publication(self, monkeypatch) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "main",
                "--head-ref",
                "HEAD",
                "--publish-review-branch",
                "--push-review-branch",
                "--review-branch-name",
                "ticket123_refactor",
                "--review-remote-name",
                "upstream",
            ],
        )

        args = _parse_args()

        assert args.publish_review_branch is True
        assert args.push_review_branch is True
        assert args.review_branch_name == "ticket123_refactor"
        assert args.review_remote_name == "upstream"

    def test_allows_configuring_pr_comment_and_creation(self, monkeypatch) -> None:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "main",
                "--head-ref",
                "HEAD",
                "--repository",
                "acme/refactor-agent",
                "--publish-pr-comment",
                "--create-review-pull-request",
            ],
        )

        args = _parse_args()

        assert args.repository == "acme/refactor-agent"
        assert args.publish_pr_comment is True
        assert args.create_review_pull_request is True