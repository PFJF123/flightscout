# Contributing to flightscout

Thanks for your interest. flightscout is a small, focused toolkit, and contributions that keep it that way are very welcome.

## Ground rules

- **Cash fares only.** flightscout deliberately does not touch award or points availability. Please do not add it.
- **Be a polite citizen of the unofficial endpoint.** flightscout reads Google Flights data through `fli`, which uses an undocumented, rate-limited endpoint. Avoid changes that increase request volume or tighten polling cadence without a clear reason.
- **Stdlib-first.** The notifier and watch layers use only the standard library on purpose. Keep new runtime dependencies out of the core; put optional features behind extras in `pyproject.toml`.

## Development setup

```bash
git clone https://github.com/PFJF123/flightscout
cd flightscout
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,cli,mcp]"
```

## Before you open a PR

```bash
ruff check .
pytest -q
```

The test suite is network-free (the `fli` calls are mocked), so it is fast and safe to run anywhere. CI runs the same checks on Python 3.10, 3.11, and 3.12; please make sure your change passes locally first.

## Pull requests

- Keep PRs scoped to a single change. Surgical diffs review faster.
- Match the existing style; do not reformat unrelated code.
- Add or update tests for behavior changes.
- Update `CHANGELOG.md` under an "Unreleased" heading.
- If you add a config option or env var, document it in `examples/config.example.toml` and the README.

## Reporting bugs

Open an issue with the command you ran, what you expected, and what happened. If a search broke, include whether plain `fli` reproduces it: the upstream endpoint changing is a common cause and helps triage quickly.

By contributing you agree your contributions are licensed under the MIT License.
