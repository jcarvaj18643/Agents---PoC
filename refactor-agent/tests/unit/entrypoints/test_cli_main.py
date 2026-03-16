"""Unit tests for the CLI argument parsing."""

import sys

import pytest

from app.entrypoints.cli import main as cli_main
from app.entrypoints.cli.main import _parse_args


class TestCliArgumentParsing:
    def test_uses_env_refs_when_cli_params_are_missing(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_BASE_REF", "env-base")
        monkeypatch.setenv("GITHUB_HEAD_REF", "env-head")
        monkeypatch.setenv("GITHUB_REPOSITORY", "env/repo")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
            ],
        )

        args = _parse_args()

        assert args.base_ref == "env-base"
        assert args.head_ref == "env-head"
        assert args.repository == "env/repo"

    def test_prefers_cli_refs_over_env_values(self, monkeypatch) -> None:
        monkeypatch.setenv("GITHUB_BASE_REF", "env-base")
        monkeypatch.setenv("GITHUB_HEAD_REF", "env-head")
        monkeypatch.setenv("GITHUB_REPOSITORY", "env/repo")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
                "--base-ref",
                "cli-base",
                "--head-ref",
                "cli-head",
                "--repository",
                "cli/repo",
            ],
        )

        args = _parse_args()

        assert args.base_ref == "cli-base"
        assert args.head_ref == "cli-head"
        assert args.repository == "cli/repo"

    def test_fails_when_refs_are_missing_in_cli_and_env(self, monkeypatch) -> None:
        class _EmptySettings:
            github_base_ref = None
            github_head_ref = None
            github_repository = None

        monkeypatch.setattr(cli_main.Settings, "from_env", classmethod(lambda cls: _EmptySettings()))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "cli",
                "--repo-path",
                "/repo",
            ],
        )

        with pytest.raises(SystemExit):
            _parse_args()

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
                "--validate-review-branch",
                "--review-branch-name",
                "ticket123_refactor",
                "--review-remote-name",
                "upstream",
            ],
        )

        args = _parse_args()

        assert args.publish_review_branch is True
        assert args.push_review_branch is True
        assert args.validate_review_branch is True
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