# Tests

Unit tests for all bot logic that does not require a live Discord connection.
Tests use [pytest](https://docs.pytest.org/) and cover four modules.

## Setup

Install pytest if it is not already installed:

```bash
pip install pytest
```

## Running the tests

From the project root:

```bash
pytest
```

Run a specific file:

```bash
pytest tests/test_db.py
```

Run a specific test class or case:

```bash
pytest tests/test_db.py::TestMatches::test_insert_and_retrieve_by_match_id
```

Run with verbose output:

```bash
pytest -v
```

## Test files

### `test_utils.py`

Tests for the two pure utility functions in `misc/utils.py`.

| Function | What is tested |
|---|---|
| `check_similarity` | Identical strings, completely different strings, partial matches, case sensitivity, symmetry |
| `split_message_blocks` | Single block, forced splits, empty input, no trailing whitespace, default 2000-char limit, no block exceeds max length |

### `test_db.py`

Tests for all read/write operations on the `DB` class (`db/db_interface.py`).
Each test gets a fresh `DB(":memory:")` instance (defined in `conftest.py`),
so there is no state leakage between tests.

| Class | What is tested |
|---|---|
| `TestMatches` | Insert, retrieve by match/message ID, filter by league, replace on duplicate, delete by league, ordering by kick-off time |
| `TestPredictions` | Insert, retrieve, upsert replace, per-match isolation, per-user retrieval, flush table |
| `TestScores` | Create, accumulate points and wins, per-league isolation, descending order, not-found returns None |
| `TestUsers` | Insert with/without emoji, upsert replace, get all, not-found returns None |
| `TestTeams` | Insert, retrieve, filter by league, same name different league, upsert replace |

### `test_api.py`

Tests for `api/api_utils.py` and `api/rapid_sports.py`.
All `requests.get` calls are patched with `unittest.mock.patch` — no real HTTP
requests are made.

| Class | What is tested |
|---|---|
| `TestGenerateHeaders` | Correct keys present, token used, host value |
| `TestValidate` | Returns parsed JSON, raises `HTTPError`, does not call `.json()` when status check fails |
| `TestGetFixtures` | Response shape, correct endpoint URL, league/season params, `from` date is after today, Oslo timezone, empty response |
| `TestGetTeams` | Response shape, correct league/season params |
| `TestGetFixtureResult` | Response shape, match ID in URL |

### `test_kupong.py`

Tests for `Kupong._get_team_display` and `Kupong._add_fixture` in
`kupong/kupong.py`.  `Kupong.__init__` calls `get_fixtures` internally, so it
is patched in every test to return an empty list.  `_message` and
`send_kupong` are not covered here because they require sending messages to a
Discord channel.

| Class | What is tested |
|---|---|
| `TestGetTeamDisplay` | Returns norsk name and emoji from DB, API name fallback, home/away default emoji, explicit league ID override |
| `TestAddFixture` | All fields stored correctly, primary league ID used by default, explicit league ID override, multiple fixtures, upsert replace |
| `TestKupongInit` | Primary fixtures loaded, no secondary league by default, secondary fixtures loaded when key provided, API called twice for secondary league |

## What is not covered

The following functions require a live Discord connection and are therefore
excluded:

- `Kupong._message` and `Kupong.send_kupong` — send messages and reactions to a channel
- `utils.store_predictions` — reads reactions from a `discord.Message`
- `utils.get_message` — fetches messages by ID from a channel
- `utils.map_teams_to_emojis` / `map_users` — iterate over guild members and emojis
- All cog commands (`KupongCog`, `AdminCog`, etc.)
- `Schedule` — wraps APScheduler and Discord channel interactions
