# Agent Notes

- Use `uv` and `uvx` for running tools or scripts.
- Format and lint with `ruff`; type check with `ty`.
- Keep Direct Inject protocol framing, escaping, and checksums aligned with the Soundweb London DI kit.
- Dev tooling runs via `uv run` (dev group is default); tests use `pytest`.
- Run `just check` and `just test` at the end of each task unless the user says to skip.
- CI scripts should be implemented as `just` tasks and invoked from workflows.
- `uv sync` is good enough to install dev dependancies.
