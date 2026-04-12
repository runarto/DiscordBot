# DiscordBot — Norwegian Football Tipping

A Discord bot for Norwegian football match predictions ("tippekupong"). Users predict match outcomes by reacting to bot-posted messages, and the bot automatically scores predictions when results are in. The bot also uses machine learning ensemble models to generate its own match outcome probabilities.

## Features

- **Weekly Kupong**: Post upcoming match messages with emoji reactions (H/U/B) for users to predict outcomes
- **Automated Scoring**: Fetch results from FotMob and score user predictions automatically
- **Leaderboards**: Track total points and weekly winners per league
- **ML Predictions**: Ensemble model (Elo + Form + Dixon-Coles goals model) displays win/draw/loss probabilities on each match message
- **Season Simulation**: Simulate remaining fixtures to forecast final table standings
- **Multi-League Support**: Eliteserien, OBOS-ligaen, and NM Cupen
- **Discord Logging**: Bot logs streamed to a dedicated Discord channel in real-time

## Tech Stack

- **Python 3.12** with **discord.py 2.5.2**
- **SQLite** for data persistence
- **APScheduler** for scheduling prediction collection at kickoff
- **scikit-learn** for ML models
- **FotMob** (web API) for fixtures and results
- **xgscore.io** for expected goals (xG) data

## Project Structure

```
main.py                 # Entry point — initializes bot, cogs, scheduler, predictor
requirements.txt
api/
  fotmob.py             # FotMob API client (fixtures, results, historical matches)
  xgscore.py            # xgscore.io client (xG data)
  api_utils.py          # Shared HTTP utilities
cogs/
  kupong.py             # /send_kupong, /send_resultater, /leaderboard
  predictor.py          # /predict, /simulate
  admin.py              # Admin utilities
  database.py           # DB management commands
  mapping.py            # Team/emoji mapping commands
kupong/
  kupong.py             # Posts match messages with predictions embedded
  results.py            # Fetches results, scores predictions, awards points
predictor/
  ensemble.py           # Weighted ensemble (30% Elo, 5% Form, 65% Goals)
  elo.py                # Elo rating predictor
  form.py               # Recent form predictor
  goals.py              # Dixon-Coles goal model with xG calibration
  ml.py                 # scikit-learn ML predictor
  simulator.py          # Season outcome simulator
db/
  db_interface.py       # Main DB access layer
  db_create.py          # Table schemas
misc/
  constants.py          # League IDs, channel IDs, team lists, emoji mappings
  schedule.py           # APScheduler wrapper
  setup.py              # Bot/predictor initialization
logger/
  log.py                # Discord log handler
tests/                  # pytest test suite
```

## Database Schema

| Table | Purpose |
|---|---|
| `matches` | Upcoming/active matches (linked to Discord messages) |
| `predictions` | User predictions per match |
| `scores` | User points and weekly wins per league |
| `users` | Discord user data |
| `teams` | Team name/emoji mappings |
| `historical_matches` | Training data for ML models (with xG) |
| `bot_predictions` | Bot's match outcome probabilities |

## Setup

### Prerequisites

- Python 3.12+
- A Discord bot token

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_discord_bot_token
LOG_NAME=discord_bot
```

Set your guild ID, channel ID, and league configuration in `misc/constants.py`.

### Running

```bash
python main.py
```

### Running as a systemd service (Linux)

Edit `discordbot.service` with your username and paths, then:

```bash
sudo cp discordbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now discordbot
```

## Tests

```bash
pytest          # Run all tests
pytest -v       # Verbose output
```

See `tests/README.md` for details on test coverage.

## Bot Workflow

### Weekly Kupong

1. Admin runs `/send_kupong`
2. Bot fetches upcoming fixtures from FotMob
3. Bot posts match messages with H/U/B reactions and ML prediction percentages
4. Users react to predict outcomes
5. Scheduler collects reactions 1 minute after kickoff

### Results & Scoring

1. Admin runs `/send_resultater`
2. Bot fetches results from FotMob
3. User predictions are scored and the leaderboard is updated
4. Results summary posted to the channel

### Predictions & Simulation

- `/predict <home> <away>` — Show ML win/draw/loss probabilities for a matchup
- `/simulate` — Monte Carlo simulation of remaining fixtures to forecast the final table

## Commands

| Command | Description |
|---|---|
| `/send_kupong` | Post upcoming match messages for user predictions |
| `/send_resultater` | Fetch results and score predictions |
| `/leaderboard` | Show the current standings |
| `/predict` | Show ML outcome probabilities for two teams |
| `/simulate` | Simulate the rest of the season |
