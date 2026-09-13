# CLAUDE.md

Guidance for Claude Code (claude.ai/code) agents working in this repository.

## Always read `CODE_STYLE.md` first

Before creating, renaming or restructuring any file/class/function, **read [`CODE_STYLE.md`](./CODE_STYLE.md)**. It is the single source of truth for conventions: language, file organisation, naming, typing, properties vs `__init__`, imports, docstrings, comments, coordinator pattern, repairs/diagnostics layout, translations, lint workflow.

For user-facing topics (entities, installation, how the portal is driven, layout diagram, useful commands, CI list), see [`README.md`](./README.md).

This file deliberately avoids restating those rules — it only adds:

1. The verification workflow agents must run after every change.
2. The architectural reasoning that is not obvious from `CODE_STYLE.md` alone.

## Origin

This repository was generated from [`ha-integration-blueprint`](https://github.com/roquerodrigo/ha-integration-blueprint). The copy was one-time and one-directional: conventions, CI and tooling evolve here independently, and blueprint changes only arrive if someone ports them over by hand.

## Verification workflow

**After every code change, always run lint then tests, in that order, before declaring the task done. Either run `scripts/lint` (a thin wrapper that only chains the four commands) or run them directly:**

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy custom_components/metragen
uv run pytest
```

- Lint runs `ruff format`, `ruff check` and `mypy` — all configured in `pyproject.toml`. Fix any failure and re-run before moving on.
- `pytest` enforces a **90 % coverage gate** (`--cov-fail-under` in `pyproject.toml`).

Both gates mirror CI (`.github/workflows/ci.yml`). Skip this only when the change literally cannot affect lint or tests (e.g., README-only edits).

## Bumping the Home Assistant version

The Home Assistant version is pinned in two places and **must be updated together**, otherwise CI, HACS and the test harness drift apart:

1. `pyproject.toml` `[dependency-groups] dev` — `homeassistant==<X.Y.Z>` (runtime/CI lint + mypy) **and** `pytest-homeassistant-custom-component==<matching release>` (the test harness ships its own pinned `homeassistant`; the two pins must come from the same HA release, otherwise lint and tests resolve different cores).
2. `hacs.json` — `"homeassistant": "<X.Y.Z>"` (minimum HA core enforced by HACS).

Verify the pairing on PyPI before committing: the `requires_dist` of `pytest-homeassistant-custom-component` must list the same `homeassistant==<X.Y.Z>` you pinned in `pyproject.toml`.

## Conventions not obvious from the code

The integration follows the HA `DataUpdateCoordinator` pattern; the module-by-module layout is in `README.md`. A few choices are not evident from reading a single file:

- State lives on `entry.runtime_data` (auto-discarded on unload), **never** on `hass.data`.
- `data/__init__.py` holds the `type` aliases (`MetragenConfigEntry`, `MetragenPayload`, `Json*`) **and** re-exports every symbol from the sibling modules, so downstream code imports everything from `.data`.
- The portal is a cookie-authenticated ASP.NET MVC site with no public API. `api.py` owns the whole protocol: the resident login form (`Portal/AcessoAoPortal`, code or e-mail plus password — not the `UserName`/`Password` form at `/metragen/`, which is the administration login), the server-side year selection (`FiltroAno`) and the Kendo grid reads. Nothing above `api.py` knows about HTML or cookies.
- The client authenticates lazily. Every grid read that comes back with an empty body raises `MetragenApiClientAuthenticationError`; `async_get_readings` catches that once, logs in and retries. A second empty body, or a login the portal rejects, propagates and the coordinator turns it into `ConfigEntryAuthFailed`.
- Each config entry gets its own `aiohttp` session from `async_create_clientsession` so the portal cookies never land in the shared session; Home Assistant detaches it when the entry unloads, so the integration must not close it.
- The coordinator payload is `Mapping[str, MetragenMeter]` keyed by `MetragenMeter.key` (`<kind>_<slugified code>`). The hot-water meter appears under both kinds (`water_aq…` for the water bill, `gas_aq…` for the heating charge) — that is what the portal reports, not a bug.
- Devices are one per meter; the device name comes from the `device.<translation_key>.name` translations with the meter code as placeholder, chosen by `MetragenMeter.device_translation_key` from the `AF`/`AQ` code prefixes.
- Meters are discovered dynamically: `sensor/__init__.py` keeps the set of known meter keys and adds entities for new ones on every coordinator update. Meters the portal stops listing keep their entities, which report unavailable; `async_remove_config_entry_device` lets the user delete them.
- Monthly history goes to long-term statistics, not to entities. `statistics.py` (`MetragenStatisticsImporter`, run by the coordinator after every successful refresh) writes the external statistics `metragen:<slugified code>_<kind>` (m³, `unit_class` volume) and `..._cost` (BRL) with `async_add_external_statistics`, named after the meter device through the cached `device` translations (plus the `monthly_cost` entity name for the cost series) so the energy picker reads like the device list. Ids carry no account prefix on purpose: meter codes include the apartment number, and shorter ids were an explicit user request. The first import walks back year by year until the portal returns no meters (`MAX_HISTORY_YEARS` cap); later imports read the last stored row with `get_last_statistics` and append only newer months, continuing its running `sum` — revised months are never rewritten. Portal errors during the import are logged and retried on the next refresh; they never fail the entity update. `manifest.json` therefore declares `recorder` in `dependencies`, and every test that sets an entry up needs the `recorder_mock` fixture.
- Reauth is wired to fire when the coordinator raises `ConfigEntryAuthFailed`. Register Repairs issues (see the sample helper in `repairs.py`) from the coordinator/setup when you detect a recoverable problem; issue strings live under `issues.<issue_id>` in the translation files.
