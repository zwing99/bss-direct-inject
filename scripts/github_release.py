from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

CHANGELOG_PATH = Path("CHANGELOG.md")


def _read_release_notes(version: str) -> str:
    lines = CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()
    header_prefix = f"## [{version}]"
    collecting = False
    notes: list[str] = []
    for line in lines:
        if line.strip().startswith(header_prefix):
            collecting = True
            continue
        if collecting and line.startswith("## ["):
            break
        if collecting:
            notes.append(line)
    content = "\n".join(notes).strip()
    if not content:
        raise SystemExit(f"No changelog notes found for {version}.")
    return content


def _repo_from_env() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set.")
    return repo


def _token_from_env() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set.")
    return token


def create_release(version: str) -> None:
    repo = _repo_from_env()
    token = _token_from_env()
    notes = _read_release_notes(version)
    payload = {
        "tag_name": f"v{version}",
        "name": f"v{version}",
        "body": notes,
        "draft": False,
        "prerelease": "a" in version or "b" in version or "rc" in version,
    }
    response = httpx.post(
        f"https://api.github.com/repos/{repo}/releases",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=payload,
        timeout=30,
    )
    if response.status_code >= 300:
        raise SystemExit(
            f"Failed to create release: {response.status_code} {response.text}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    args = parser.parse_args()
    create_release(args.version)


if __name__ == "__main__":
    main()
