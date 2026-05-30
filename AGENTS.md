# AGENTS.md

Guidance for coding agents working in this repository.

## Project Overview

This is a Python Discord bot for Norwegian football tipping. It posts weekly
match coupons, stores user predictions from reactions, scores predictions after
results are available, maintains leaderboards, and shows model-generated match
probabilities.

Core runtime flow:

- `main.py` creates the shared `DB("infobase.db")`, loads `.env`, configures
  logging, builds the Discord bot, registers cogs, starts APScheduler, and
  trains the predictor on startup.
- `cogs/` contains Discord slash command surfaces.
- `kupong/` contains match-message posting and result scoring logic.
- `api/` contains FotMob and xgscore.io clients plus parsing utilities.
- `db/` contains the SQLite schema and the `DB` access wrapper.
- `predictor/` contains the ensemble prediction model and simulation logic.
- `misc/` contains constants, dataclasses, scheduler setup, and shared helpers.
- `tests/` contains unit tests for logic that does not require a live Discord
  connection.

## Environment

Use Python 3.12 or newer.

Typical setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Runtime configuration is stored in `.env`, which is intentionally ignored by
git. Do not print, copy, or commit secrets from `.env`.

Expected environment variables:

- `BOT_TOKEN`: Discord bot token.
- `LOG_NAME`: optional logger name used by local configuration.

## Running

Run the live bot from the repository root:

```bash
python main.py
```

Starting the bot performs live Discord and network work:

- Connects to Discord.
- Fetches/caches current and historical FotMob data.
- Fetches current-season xG data from xgscore.io.
- Trains the ensemble predictor.
- Starts scheduled jobs for unstored match predictions.

Do not run `python main.py` casually during code edits unless the user expects
live bot behavior.

## Tests

Run tests from the repository root:

```bash
pytest -q
```

The tests use `pytest.ini` with `pythonpath = .` and `testpaths = tests`.
Database tests use fresh in-memory SQLite databases via `DB(":memory:")`.
Network and Discord-facing behavior should be mocked in tests.

Current local note: `pytest -q` fails at collection if `scikit-learn` is not
installed, because importing `predictor` pulls in `predictor.ml`. Install
`requirements.txt` before treating test failures as code regressions.

## Database And Runtime Artifacts

The production SQLite database is `infobase.db`. There is also `test.db` and
timestamped DB files under `backups/`.

Rules of thumb:

- Treat `infobase.db`, `test.db`, and `backups/*.db` as runtime data.
- Do not modify, delete, reset, or reformat DB files unless the user explicitly
  asks.
- Commands that score results or store predictions can mutate the DB. Many of
  them create backups first through `misc.utils.backup_database`.
- Schema lives in `db/db_create.py`; higher-level access belongs in
  `db/db_interface.py`; raw SQL helpers belong in `db/db_read_write.py`.
- `matches.match_id` is the FotMob match ID. `matches.message_id` is the
  Discord message ID.

## Leagues And Prediction Labels

League configuration lives in `misc/constants.py`:

- `ELITE`: Eliteserien.
- `OBOS`: OBOS-ligaen.
- `Cupen`: NM Cupen.

Internal prediction labels are:

- `H`: home win.
- `D`: draw.
- `A`: away win.

User-facing Norwegian coupon labels display draw as `U` and away as `B`.
Be careful not to mix the internal `D` value with the displayed `U` label in DB
or scoring code.

## Discord Command Surfaces

`main.py` manually instantiates cogs in `load_cogs()`. Prefer following the
existing constructor pattern where cogs receive the shared `bot` and `db`.

Major cogs:

- `cogs/kupong.py`: `/send_kupong`, `/send_resultater`, leaderboard,
  prediction storage, message deletion, cheater reports.
- `cogs/predictor.py`: `/predict` and `/simulate`.
- `cogs/database.py`: table/user/score utility commands.
- `cogs/mapping.py`: role, team, and user emoji mapping commands.
- `cogs/admin.py`: administrative message and backup restore helpers.

Commands generally defer responses and send ephemeral followups for admin
operations. Keep that behavior consistent.

## API Notes

FotMob integration is HTML-page based. `api/api_utils.py` extracts the
`__NEXT_DATA__` script payload and normalizes match dictionaries. xG data comes
from `api/xgscore.py`.

When changing API code:

- Keep requests bounded with timeouts.
- Prefer parser/normalizer helpers over duplicating response-shape traversal.
- Keep network calls out of unit tests by patching `requests.get` or the
  relevant API wrapper.
- Be cautious with current-season behavior: startup intentionally refetches the
  current season while caching older seasons.

## Predictor Notes

`misc.setup.setup_predictor()` builds an `EnsemblePredictor` from:

- `EloPredictor` weight `0.30`.
- `FormPredictor` weight `0.05`.
- `GoalsPredictor` weight `0.65`.

The goals model uses xG when available, actual goals otherwise, and calibrates
Dixon-Coles rho after training. Cross-league quality is derived from ELO league
averages.

Useful script:

```bash
python -m scripts.eval_ml
```

It evaluates current ensemble variants against cached DB match history.

## Coding Conventions

- Follow the existing simple module layout; avoid adding new frameworks.
- Keep bot command logic thin when possible and put reusable behavior in
  `kupong/`, `predictor/`, `api/`, `db/`, or `misc/`.
- Use dataclasses from `misc/dataclasses.py` for DB-facing data shapes.
- Preserve timezone-aware kickoff handling. Scheduler runtime uses
  `Europe/Oslo`; FotMob parsing normalizes UTC timestamps.
- Use parameterized SQL for values. Do not expand the existing raw table-name
  helpers to accept user-controlled input without whitelisting.
- Keep tests focused on pure logic and mocked boundaries, since live Discord
  behavior is not covered by unit tests.
- Avoid broad rewrites of Norwegian user-facing strings unless the task is
  specifically about copy or localization.

## Before Finishing Changes

For most code edits, run:

```bash
pytest -q
```

If tests cannot run because dependencies are missing, state that clearly and
include the import or command failure. Also check `git status --short` and avoid
touching unrelated runtime DB or backup changes.
