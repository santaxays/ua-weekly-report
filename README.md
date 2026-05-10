# UA Weekly Report Bot

A Python bot that pulls UA (User Acquisition) data and posts a weekly summary to Slack.

## Setup

Run these commands in your terminal from the project folder:

```bash
# 1. Create a virtual environment (isolated Python workspace)
python3.11 -m venv .venv

# 2. Activate it (you'll need to do this every time you open a new terminal)
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example env file and fill in your real Slack credentials
cp .env.example .env
# Then open .env in a text editor and replace the placeholder values

# 5. Run the bot
python src/main.py
```
