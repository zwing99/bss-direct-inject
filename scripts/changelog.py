from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CHANGELOG_PATH = Path("CHANGELOG.md")
VERSION_RE = re.compile(r"^## \[(?P<version>[^]]+)\]")
TAG_RE = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+)$")


def _read_changelog() -> list[str]:
    if not CHANGELOG_PATH.exists():
        raise SystemExit("CHANGELOG.md not found.")
    return CHANGELOG_PATH.read_text(encoding="utf-8").splitlines()


def latest_release_version() -> str | None:
    for line in _read_changelog():
        match = VERSION_RE.match(line.strip())
        if not match:
            continue
        version = match.group("version")
        if version.lower() == "unreleased":
            continue
        return version
    return None


def _parse_core_version(version: str) -> tuple[int, int, int]:
    match = TAG_RE.match(version)
    if not match:
        raise ValueError(f"Invalid version: {version}")
    major, minor, patch = match.group("version").split(".")
    return int(major), int(minor), int(patch)


def assert_bumped_from_tag(latest_tag: str | None) -> None:
    if not latest_tag:
        return
    changelog_version = latest_release_version()
    if not changelog_version:
        raise SystemExit("No release version found in CHANGELOG.md.")
    tag_version = TAG_RE.match(latest_tag)
    if not tag_version:
        raise SystemExit(f"Invalid tag format: {latest_tag}")
    if _parse_core_version(changelog_version) <= _parse_core_version(
        tag_version.group("version")
    ):
        raise SystemExit(
            "Changelog version "
            f"{changelog_version} must be greater than tag {latest_tag}."
        )


def assert_version(version: str) -> None:
    versions = []
    for line in _read_changelog():
        match = VERSION_RE.match(line.strip())
        if match:
            versions.append(match.group("version"))
    if version not in versions:
        raise SystemExit(f"Version {version} not found in CHANGELOG.md.")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("latest-version")
    assert_bumped = subparsers.add_parser("assert-bumped")
    assert_bumped.add_argument("--tag", required=False)

    assert_parser = subparsers.add_parser("assert-version")
    assert_parser.add_argument("version")

    args = parser.parse_args()

    if args.command == "latest-version":
        version = latest_release_version()
        if version:
            print(version)
        return

    if args.command == "assert-bumped":
        assert_bumped_from_tag(args.tag)
        return

    if args.command == "assert-version":
        assert_version(args.version)
        return

    raise SystemExit("Unknown command.")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
