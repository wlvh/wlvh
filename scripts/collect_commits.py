"""Collect owned repository commit messages through the GitHub CLI.

Purpose:
    Build a local JSONL audit file that can be classified into a public
    aggregate topic map without publishing raw commit messages.

Call graph:
    main -> parse_args -> collect_repositories -> collect_commits -> write_rows
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CollectConfig:
    """Runtime parameters for repository and commit collection.

    Attributes:
        owner: GitHub account whose repositories should be inspected.
        output_path: UTF-8 JSONL file for raw local commit records.
        include_private: Whether private repositories are included locally.
        include_forks: Whether forked repositories are included.
        include_archived: Whether archived repositories are included.
        per_page: GitHub API page size in the inclusive range 1..100.
        max_pages: Optional safety cap; 0 means collect every page.
    """

    owner: str
    output_path: Path
    include_private: bool
    include_forks: bool
    include_archived: bool
    per_page: int
    max_pages: int


def parse_args() -> CollectConfig:
    """Parse explicit command-line parameters into a validated config."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-private", action="store_true")
    parser.add_argument("--include-forks", action="store_true")
    parser.add_argument("--include-archived", action="store_true")
    parser.add_argument("--per-page", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=0)
    args = parser.parse_args()

    if args.per_page < 1 or args.per_page > 100:
        raise ValueError("--per-page must be between 1 and 100")
    if args.max_pages < 0:
        raise ValueError("--max-pages must be 0 or greater")

    return CollectConfig(
        owner=args.owner,
        output_path=Path(args.output),
        include_private=args.include_private,
        include_forks=args.include_forks,
        include_archived=args.include_archived,
        per_page=args.per_page,
        max_pages=args.max_pages,
    )


def run_json(command: list[str]) -> Any:
    """Run a command that must return UTF-8 JSON and fail fast on errors."""

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\n{result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def collect_repositories(config: CollectConfig) -> list[dict[str, Any]]:
    """Return repositories that match the privacy, fork, and archive filters."""

    repos = run_json(
        command=[
            "gh",
            "repo",
            "list",
            config.owner,
            "--limit",
            "1000",
            "--json",
            "name,isPrivate,isFork,isArchived,defaultBranchRef",
        ],
    )

    selected: list[dict[str, Any]] = []
    for repo in repos:
        # These filters keep the published chart about owned work instead of
        # inherited upstream histories or dormant archives.
        if repo["isPrivate"] and not config.include_private:
            continue
        if repo["isFork"] and not config.include_forks:
            continue
        if repo["isArchived"] and not config.include_archived:
            continue
        if repo["defaultBranchRef"] is None:
            continue
        selected.append(repo)
    return selected


def commit_rows_for_repo(
    *,
    config: CollectConfig,
    repo: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch default-branch commit rows for a single repository."""

    repo_name = repo["name"]
    branch_name = repo["defaultBranchRef"]["name"]
    rows: list[dict[str, Any]] = []
    page = 1

    while True:
        # Page explicitly so partial failures show the exact repo/page boundary.
        commits = run_json(
            command=[
                "gh",
                "api",
                "-X",
                "GET",
                f"repos/{config.owner}/{repo_name}/commits",
                "-f",
                f"sha={branch_name}",
                "-f",
                f"per_page={config.per_page}",
                "-f",
                f"page={page}",
            ],
        )
        if not isinstance(commits, list):
            raise TypeError(f"Unexpected commits payload for {repo_name}")
        if len(commits) == 0:
            break

        for commit_item in commits:
            message = commit_item["commit"]["message"]
            subject, body = split_message(message=message)
            rows.append(
                {
                    "repo": repo_name,
                    "repo_private": repo["isPrivate"],
                    "sha": commit_item["sha"],
                    "date": commit_item["commit"]["author"]["date"],
                    "subject": subject,
                    "body": body,
                    "is_merge": subject.startswith("Merge "),
                }
            )

        if len(commits) < config.per_page:
            break
        if config.max_pages > 0 and page >= config.max_pages:
            break
        page += 1
    return rows


def split_message(*, message: str) -> tuple[str, str]:
    """Split a commit message into subject and body strings."""

    parts = message.split("\n\n", maxsplit=1)
    if len(parts) == 1:
        return parts[0].strip(), ""
    return parts[0].strip(), parts[1].strip()


def collect_commits(config: CollectConfig) -> list[dict[str, Any]]:
    """Collect commit rows across all selected repositories."""

    rows: list[dict[str, Any]] = []
    for repo in collect_repositories(config=config):
        repo_rows = commit_rows_for_repo(config=config, repo=repo)
        print(f"{repo['name']}: {len(repo_rows)} commits")
        rows.extend(repo_rows)
    return rows


def write_rows(*, output_path: Path, rows: list[dict[str, Any]]) -> None:
    """Write UTF-8 JSONL rows in deterministic date order."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_rows = sorted(rows, key=lambda item: (item["date"], item["repo"]))
    with output_path.open("w", encoding="utf-8") as output_file:
        for row in sorted_rows:
            output_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    """Collect commit metadata and write the local raw JSONL file."""

    config = parse_args()
    rows = collect_commits(config=config)
    write_rows(output_path=config.output_path, rows=rows)
    print(f"total: {len(rows)} commits -> {config.output_path}")


if __name__ == "__main__":
    main()
