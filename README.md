# UA Weekly Report Bot

> Automated weekly performance report for User Acquisition teams.
> CSV (or AppsFlyer API) → metrics → Claude AI insights → Slack message, every Monday at 09:00.

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![Anthropic Claude](https://img.shields.io/badge/Claude-Sonnet%204.5-D97757?logo=anthropic&logoColor=white)
![Slack](https://img.shields.io/badge/Slack-Block%20Kit-4A154B?logo=slack&logoColor=white)
![Status](https://img.shields.io/badge/status-in%20development-yellow)

---

## Why this exists

Most UA teams I've worked with spend **~6 hours every week** putting together a weekly performance report: pulling data from AppsFlyer, building tables in a spreadsheet, hand-writing a few takeaways for the team Slack.

This bot does the whole thing in 30 seconds, every Monday, automatically. The Claude-powered insights section is what makes it different from a "dashboard with cron" — it reads the numbers like a senior media buyer would, then writes 2–3 specific observations and recommendations.

Built as part of [ilyasirotin.com](https://ilyasirotin.com) — UA consulting + AI automations for mobile app teams.

---

## What the report looks like

A Monday morning Slack message looks roughly like this:

```
📊 UA Weekly · Apr 28 – May 4

Spend: $32,900   ↑ 7.3%
Installs: 9,136  ↑ 3.3%
CPI: $3.60       ↑ 3.9%
ROAS D7: 62.8%   ↓ 5.1%
CTR: 2.56%       ↓ 3.0%

💡 Insights of the week
Spend is growing faster than installs (+7.3% vs +3.3%),
pushing CPI up and ROAS down — efficiency is slipping.

• SummerBoost_US runs at $1.92 CPI with 79.7% ROAS D7 —
  almost half the average. Strong candidate for budget scaling.
• RetargetPro_UK and InstallDrive_CA hold high ROAS (93.9% and
  80.7%) but at $3.90 CPI — typical of narrow but high-LTV
  audiences; worth checking if there's headroom.
• CTR dropped 3% across the board with ROAS D7 down 5% — the
  fatigue isn't isolated to one campaign, suggests rotation
  is overdue across geos.

Actions:
• Lift SummerBoost_US budget; clone the creative/audience
  pattern into CA and AU.
• A/B test new creative formats in UK and CA to arrest the
  CTR decline.

Top 3 by ROAS D7
1. RetargetPro_UK — 93.9% | CPI $3.88 | 1,112 installs
2. InstallDrive_CA — 80.7% | CPI $3.94 | 977 installs
3. SummerBoost_US — 79.7% | CPI $1.92 | 1,675 installs

Burning creatives
• CreativeTest_UK — CTR ↓39.2% | CPI ↑33.4% ($2.97 → $3.97)
```

---

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌────────┐
│   AppsFlyer │ →  │  metrics.py  │ →  │ claude       │ →  │ Slack  │
│   / CSV     │    │  pandas calc │    │ analyst.py   │    │ Block  │
└─────────────┘    └──────────────┘    └──────────────┘    │ Kit    │
                                              ↑             └────────┘
                                       Claude Sonnet 4.5
                                       structured JSON
```

- **`src/metrics.py`** — pandas aggregation, week-over-week diffs, burning-creative detection
- **`src/claude_analyst.py`** — sends the metrics payload to Claude API, parses JSON insights, fails gracefully
- **`src/report_builder.py`** — composes Slack Block Kit message
- **`src/slack_client.py`** — thin wrapper over `slack_sdk`
- **`src/main.py`** — entrypoint that ties it all together

The Claude module returns `None` on any failure (no API key, network error, malformed JSON). The report still ships to Slack — just without the insights block. **Better to send a partial report than no report.**

---

## Setup

Requires Python 3.11+ and a Mac/Linux shell.

```bash
# 1. Clone
git clone https://github.com/santaxays/ua-weekly-report.git
cd ua-weekly-report

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env and fill in your real values (see below)

# 5. Run
python src/main.py
```

You should see `Sent OK` in the terminal, and a fresh report in your Slack channel.

---

## Configuration

The bot reads three environment variables from `.env`:

| Variable | Where to get it | Example |
|---|---|---|
| `SLACK_BOT_TOKEN` | https://api.slack.com/apps → your app → OAuth & Permissions | `xoxb-...` |
| `SLACK_CHANNEL_ID` | Slack → channel details → Channel ID at the bottom | `C0123ABC456` |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys | `sk-ant-api03-...` |

The Slack bot needs the `chat:write` scope and must be invited to the target channel (`/invite @your-bot-name`).

---

## Tests

```bash
pytest
```

Three test files cover metric calculations and Claude API mocking. They run in under 2 seconds and don't hit the real API.

---

## Roadmap

- [x] Slack pipeline (session 1)
- [x] CSV parsing + metrics (session 2)
- [x] Claude AI insights (session 3)
- [ ] AppsFlyer API integration (session 4)
- [ ] Cron schedule via GitHub Actions (session 5)
- [ ] Multi-client config (one repo, many app/Slack pairs)
- [ ] Anomaly detection beyond burning creatives (network-level, geo-level)

---

## Why open source

I build automations for UA teams as part of my consulting practice — see [ilyasirotin.com](https://ilyasirotin.com) for the full list. Publishing the code does three things:

1. Lets potential clients see how I actually write things, not how a sales page promises.
2. Lets other UA practitioners adapt it for their own use, no strings attached.
3. Keeps me honest. If the code is bad, anyone can see.

If you're a UA team looking to automate your own version of this — [book a call](https://calendly.com/ilyasirotin/free-intro-call-20-min) and we'll figure out the right scope.

---

## License

MIT — do whatever you want with it. Attribution appreciated but not required.

---

Made by [Ilya Sirotin](https://ilyasirotin.com) · UA Lead × AI engineer · in performance marketing since 2014
