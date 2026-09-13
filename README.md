# Metragen for Home Assistant

[![CI](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml/badge.svg)](https://github.com/roquerodrigo/ha-metragen/actions/workflows/ci.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

[![Open your Home Assistant instance and open the repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=roquerodrigo&repository=ha-metragen&category=integration)

---

Custom [Home Assistant](https://www.home-assistant.io/) integration for the
[Sistema Metragen](https://www.sistemametragen.com.br/metragen) resident portal,
the individualized water and gas metering service used by Brazilian
condominiums. It signs in with the same credentials you use on the portal and
turns every meter listed under your apartment into a device with its readings.

## Entities

One device is created per meter the portal lists, named after the meter code
and what it measures — "AF2616 Cold Water", "AQ2616 Hot Water", "AQ2616 Gas" —
each with four sensors:

| Sensor | Unit | Class | What it reports |
|---|---|---|---|
| Reading | m³ | water / gas, `total_increasing` | Counter value of the latest published reading. Use it as a water or gas source in the Energy dashboard. |
| Monthly Consumption | m³ | water / gas, `total` | Volume billed in the latest reading period; `last_reset` is the first day of that month. |
| Monthly Cost | BRL | monetary, `total` | Amount charged for the meter in that period. |
| Yearly Consumption | m³ | water / gas, `total` | Volume accumulated since the first reading of the year. |

Every sensor exposes `meter_code`, `year` and `month` as attributes so you know
which billing period the state refers to. The portal publishes readings once a
month, so the default polling interval is one hour (configurable from the
integration options).

## History and the Energy dashboard

A sensor state only carries the latest published reading, so the month-by-month
history the portal keeps is imported into Home Assistant's long-term statistics
instead. Every meter gets two external statistics:

| Statistic id | Unit | What it holds |
|---|---|---|
| `metragen:<code>_<kind>` | m³ | Volume of each month, with the meter reading as state |
| `metragen:<code>_<kind>_cost` | BRL | Amount charged for each month |

`<code>` is the meter code shown on the portal and `<kind>` is `water` or
`gas`, e.g. `metragen:af2616_water` or `metragen:aq2616_gas`. The series are
named like the meter devices ("AF2616 Cold Water", "AQ2616 Gas"), so the
energy dashboard picker reads the same as the device list. Each month's value
lands on the first day of that month.

The first refresh walks back one year at a time until the portal reports no
meters at all (at most 10 years); later refreshes only append months newer than
the last stored one. Pick the consumption statistic as a water or gas source in
*Settings → Dashboards → Energy*, or plot either series with a statistics graph
card. Removing the integration keeps the statistics; delete them from
*Developer tools → Statistics* if you no longer want them.

## Installation

### HACS

1. Add `https://github.com/roquerodrigo/ha-metragen` as a custom repository of
   type *Integration*, or click the badge above.
2. Install **Metragen** and restart Home Assistant.
3. Go to *Settings → Devices & services → Add integration*, pick **Metragen**
   and enter the code or e-mail and the password you registered on the resident
   portal (the *Registre-se* form).

### Manual

Copy `custom_components/metragen/` into the `custom_components/` directory of
your Home Assistant configuration and restart.

## How it works

The portal has no public API; the integration drives the same endpoints the
resident area of the website uses:

1. `POST /Portal/AcessoAoPortal` with the code or e-mail and the password the
   resident registered on the portal. A rejected login redirects back to the
   login page instead of failing the request.
2. `POST /Portal/AreaMorador` and `POST /Portal/FiltroAno` select the resident
   area and the year on the server-side session.
3. `POST /Portal/LeiturasMorador_Read` and `POST /Portal/LeiturasMoradorGas_Read`
   return the water and gas grids as JSON. An empty body means the session
   lapsed, so the client signs in again and retries once.

Readings are published monthly, so early in a year the current year may have
no rows yet; each kind without rows falls back to the previous year so the
latest reading keeps being reported across the turn of the year. Short portal
outages are absorbed for 24 hours before the entities become unavailable, and
rejected credentials start the re-authentication flow.

## Development

```bash
scripts/setup                              # create .venv and install deps (uv sync)
scripts/develop                            # start Home Assistant in debug mode with the integration loaded
scripts/lint                               # ruff format --check, ruff check, mypy and pytest
uv run ruff format --check .               # check formatting
uv run ruff check .                        # lint
uv run mypy custom_components/metragen     # type-check
uv run pytest                              # run tests with the 90 % coverage gate
```

Both scripts run through `uv`, which manages `./.venv` automatically. HA runs
with config in `config/` and `PYTHONPATH` pointing at `custom_components/` — no
symlinks. To recreate entity/device IDs during development:

```bash
rm config/.storage/core.entity_registry config/.storage/core.device_registry
```

### Testing in Docker

`compose.yaml` runs the Home Assistant release the tests are pinned to, with
`config/` as its configuration directory and `custom_components/metragen/`
mounted read-only inside it, so the container always runs the working tree:

```bash
docker compose up -d          # start Home Assistant on http://localhost:8123
docker compose logs -f        # follow the log (the integration logs at debug level)
docker compose restart        # reload the integration after a code change
docker compose down           # stop; config/ keeps the onboarding, users and entries
```

On first start complete the onboarding, then add **Metragen** under
*Settings → Devices & services*. `config/` is shared with `scripts/develop`,
so do not run both at the same time.

Conventions for contributors live in [`CODE_STYLE.md`](./CODE_STYLE.md);
architectural notes for AI agents in [`CLAUDE.md`](./CLAUDE.md). Install the
pre-commit hooks once per clone with `pre-commit install`.

## Layout

```
custom_components/metragen/
├── __init__.py        # async_setup_entry / unload / reload / remove device
├── api.py             # portal client: login, year selection, grid reads
├── brand/             # brand assets
├── config_flow.py     # user / reauth / reconfigure steps
├── const.py           # DOMAIN, LOGGER, portal URL, ATTRIBUTION, scan-interval defaults
├── coordinator.py     # DataUpdateCoordinator with year fallback and outage grace period
├── data/              # one TypedDict/dataclass per file; type aliases in __init__.py
│   ├── meter.py       # MetragenMeter: code, kind, readings, derived values
│   ├── meter_kind.py  # water / gas
│   ├── meter_reading.py
│   ├── readings.py    # meters of one year, by kind
│   ├── reading_row.py # raw grid row shape
│   ├── read_response.py
│   └── …              # config, options, diagnostics and runtime shapes
├── diagnostics.py     # downloadable diagnostics with credential redaction
├── entity.py          # base CoordinatorEntity bound to one meter
├── exceptions/        # one file per exception class
├── icons.json         # entity icons keyed by translation_key
├── manifest.json
├── options_flow.py    # OptionsFlow with scan_interval
├── repairs.py         # Repair platform
├── sensor/            # one file per sensor class
└── translations/
    ├── en.json
    └── pt-BR.json
```

## CI

All workflows call the reusable workflows in [`roquerodrigo/workflows`](https://github.com/roquerodrigo/workflows):

- **`ci.yml`** — ruff (check + format) + mypy, pytest with the coverage gate, and `hassfest` validation (the HACS validator is off while the repository is private); push/PR to `main`
- **`release.yml`** — release-please, gated on a green CI run on `main`
- **`auto-assign.yml`** — assigns new issues/PRs to the code owner

## License

[MIT](LICENSE)
