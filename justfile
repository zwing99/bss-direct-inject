fmt:
    uv run ruff format .

lint:
    uv run ruff check .

lint-fix:
    uv run ruff check --fix .

typecheck:
    uv run ty check

test:
    uv run pytest --cov=bss_direct_inject --cov-report=term-missing --cov-report=html

test-ci:
    bash -c 'uv run pytest --cov=bss_direct_inject --cov-report=term-missing --cov-report=html | tee coverage.txt'

check:
    just fmt
    just lint
    just typecheck

build:
    uv build

publish:
    uv publish

ci-sync:
    uv sync

changelog-latest:
    uv run python scripts/changelog.py latest-version

changelog-assert-bumped TAG:
    uv run python scripts/changelog.py assert-bumped --tag "{{TAG}}"

changelog-assert-version VERSION:
    uv run python scripts/changelog.py assert-version "{{VERSION}}"

changelog-ci:
    bash -c 'VERSION="$(uv run python scripts/changelog.py latest-version || true)"; \
        VERSION="${VERSION:-}"; \
        LATEST_TAG="$(git tag --sort=version:refname | tail -n 1 || true)"; \
        if [ -n "${LATEST_TAG:-}" ]; then uv run python scripts/changelog.py assert-bumped --tag "$LATEST_TAG"; fi; \
        if [ -z "$VERSION" ]; then echo "has_release=false"; else echo "has_release=true"; echo "version=$VERSION"; fi'

set-alpha-version VERSION BUILD:
    uv version "{{VERSION}}a{{BUILD}}"

set-release-version VERSION:
    uv version "{{VERSION}}"

tag-release VERSION:
    git config user.name "${GIT_USER_NAME:-github-actions[bot]}"
    git config user.email "${GIT_USER_EMAIL:-41898282+github-actions[bot]@users.noreply.github.com}"
    git tag -a "v{{VERSION}}" -m "Release v{{VERSION}}"
    git push origin "v{{VERSION}}"

github-release VERSION:
    uv run python scripts/github_release.py "{{VERSION}}"

coverage-summary:
    uv run python scripts/coverage_summary.py coverage.txt
