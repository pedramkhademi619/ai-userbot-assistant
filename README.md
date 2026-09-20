<p align="center">
  <img src="docs/logo.svg" alt="AI Userbot Assistant" width="640">
</p>

<p align="center">
  <a href="https://github.com/pedramkhademi619/ai-userbot-assistant/actions/workflows/ci.yml"><img src="https://github.com/pedramkhademi619/ai-userbot-assistant/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
</p>

A desktop app that turns your personal messenger account into an
AI-powered auto-reply assistant. It logs in as *you* (a "userbot"),
replies to private messages with an OpenAI-compatible model on your
behalf, and ships with a full Tkinter GUI so non-technical users can set
it up without touching a config file.

**Rubika and Telegram are supported today**; the architecture is
deliberately platform-agnostic (see [How it works](#how-it-works)) so
more messengers can be added over time — see
[Contributing](#contributing).

## Features

- **Multiple messengers, one codebase** — connect to Rubika (via [rubpy](https://pypi.org/project/rubpy/))
  or Telegram (via [Telethon](https://github.com/LonamiWebs/Telethon)) as your own account, not a bot API bot.
  Built to grow: adding another messenger means a new runtime module, not a rewrite.
- **Any OpenAI-compatible backend** — point it at OpenAI, Azure OpenAI, or
  any self-hosted / third-party API that speaks the same protocol, by
  changing `BASE_URL` and `MODEL`.
- **Guided onboarding wizard** — platform picker → phone/OTP login (+ 2FA
  when Telegram asks for it) → AI backend setup, all inside the app.
  No manual `.env` editing required.
- **Editable system prompt from the GUI** — preview, append notes, or
  fully rewrite the assistant's persona without leaving the chat screen.
- **Encrypted secrets storage** — API keys and phone numbers are kept out
  of the project directory, encrypted with Windows DPAPI (or Fernet as a
  cross-platform fallback), never in plain-text `.env` files.
- **Per-user rate limiting, response caching, and request locks** — keeps
  the bot responsive and protects your AI budget from spam or duplicate
  requests.
- **Live chat view** — watch every incoming/outgoing message, cache hit,
  and error in a real-time dashboard while the bot runs.
- **Start / Stop / Pause controls** — the bot thread can be paused without
  disconnecting, and cleanly reconnected without a restart.

## How it works

```
┌─────────────┐      events       ┌──────────────────┐
│  bot thread │ ────────────────► │   Tkinter GUI     │
│ (Rubika or  │                   │  (bot/gui/*)       │
│  Telegram)  │ ◄──────────────── │                    │
└──────┬──────┘   OTP / 2FA input └──────────────────┘
       │
       ▼
┌─────────────────┐     ┌───────────────────┐
│ bot/handlers.py  │────►│  bot/ai.py         │──► OpenAI-compatible API
│ telegram_runtime │     │  (prompt + history) │
└─────────────────┘     └───────────────────┘
       │
       ▼
┌─────────────────┐
│ bot/memory.py    │  rate limiting · response cache · per-user locks
└─────────────────┘
```

The bot runtime and the GUI never call each other directly — they
communicate through a tiny publish/subscribe event bus
([bot/events.py](bot/events.py)). That keeps the GUI optional: the same
runtime can be driven headlessly from [run.py](run.py) for a console-only
setup.

### Project layout

```
.
├── run.py                    # Console entry point: python run.py
├── run_gui.py                 # GUI entry point: python run_gui.py
├── system_prompt.txt          # Editable assistant persona / instructions
├── .env.example                # Copy to .env — non-secret settings only
├── requirements.txt
└── bot/
    ├── config.py               # Env vars + secrets loading, reload, persistence
    ├── secrets_store.py        # Encrypted key/value store (DPAPI / Fernet)
    ├── clients.py               # Shared rubpy Client + AsyncOpenAI instances
    ├── memory.py                 # Conversation history, rate limit, cache, locks
    ├── ai.py                      # Prompt building + model calls
    ├── handlers.py                # Rubika private-message handler
    ├── telegram_runtime.py        # Telegram (Telethon) login + message handler
    ├── auth.py / auth_bridge.py    # Background login flow, GUI <-> input() bridge
    ├── events.py                   # Publish/subscribe event bus
    ├── state.py                     # Shared bot-thread state
    └── gui/
        ├── dashboard.py             # Top-level window, composed from the mixins below
        ├── wizard.py                 # Onboarding: platform pick, login, AI setup
        ├── chat_view.py               # Live chat + sidebar controls
        ├── settings_view.py           # Post-login settings editor
        ├── dialogs.py                  # Error / OTP / 2FA modal dialogs
        ├── event_pump.py               # Polls the event bus, updates widgets
        ├── theme.py                     # Shared colors/fonts
        └── widgets.py                   # Small reusable Tk widget helpers
```

## Requirements

- Python 3.11+
- Windows is fully supported out of the box (secrets are encrypted with
  DPAPI). On Linux/macOS the app falls back to a `cryptography`-based
  encrypted store — install it via `requirements.txt` (already included).
- A Rubika account and/or a Telegram account (with an API ID/hash from
  [my.telegram.org](https://my.telegram.org) for the Telegram path).
- An OpenAI-compatible API key.

## Installation

```bash
git clone https://github.com/pedramkhademi619/ai-userbot-assistant.git
cd ai-userbot-assistant

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
cp .env.example .env         # optional — the GUI wizard can set everything up for you
```

## Usage

### GUI (recommended)

```bash
python run_gui.py
```

On first launch you'll be walked through:

1. **Platform** — Rubika or Telegram.
2. **Login** — phone number + OTP (Telegram also asks for your
   two-factor password if you have one enabled).
3. **AI setup** — API key, base URL, model, token/history limits, and the
   system prompt.

After that, the app opens straight into the chat view. Press **Start** to
bring the bot online; **Stop** pauses it without logging out.

> Session files (`*.rp` for Rubika, `*.session` for Telegram) are created
> in the project root, so always run the app from there.

### Console mode

```bash
python run.py
```

Runs the Rubika bot without a GUI, using whatever is already configured
in `.env` / the secrets store. There is currently no console-only path
for the Telegram runtime or the first-time login flow — use the GUI at
least once to log in.

## Configuration

Non-secret tuning values live in `.env` (see [.env.example](.env.example)
for the full list — history length, rate limits, timeouts, etc.).

Anything sensitive — API keys, phone numbers, Telegram API credentials —
is written to an encrypted SQLite store outside the project directory
(`%USERPROFILE%\.rubika_bot\secrets.db` on Windows, `~/.rubika_bot/secrets.db`
elsewhere) by [bot/secrets_store.py](bot/secrets_store.py). You normally
never touch this file directly; the wizard and settings screen manage it
for you.

The assistant's personality and knowledge about the account owner live in
[system_prompt.txt](system_prompt.txt), plain text, editable from the
chat screen's sidebar.

## Security notes

- Secrets are encrypted at rest (Windows DPAPI, or Fernet via
  `cryptography` elsewhere) and stored outside the repo, never committed.
- `.env`, `*.rp`, `*.session`, and `*.session-journal` are all gitignored
  — double-check before committing if you fork this.
- Logging in as a userbot (especially on Telegram) puts automated traffic
  through your personal account. Read the platform's terms of service —
  aggressive or bulk automation can get an account flagged or banned.
  Use reasonable rate limits and only automate your own private chats.

## Contributing

Issues and pull requests are welcome. **Adding support for another
messenger is explicitly encouraged** — open a pull request for it and
it'll get reviewed and merged. A new platform generally means:

- A runtime module similar to [bot/handlers.py](bot/handlers.py) /
  [bot/telegram_runtime.py](bot/telegram_runtime.py) that reuses
  [bot/ai.py](bot/ai.py) and [bot/memory.py](bot/memory.py) as-is.
- New onboarding steps in [bot/gui/wizard.py](bot/gui/wizard.py) and an
  entry in `VALID_PLATFORMS` ([bot/config.py](bot/config.py)).
- Whatever login/session credentials that platform needs, added to
  `SECRET_KEYS` in [bot/config.py](bot/config.py) so they go through the
  encrypted secrets store rather than `.env`.

Other good starting points:

- A console-only login flow for Telegram (today it requires the GUI).
- Screenshots/GIFs for this README (`docs/screenshot.png`).

Please run the checks below before opening a PR:

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

## License

Released under the [MIT License](LICENSE).

## Author

Made by [Pedram Khademi](https://github.com/pedramkhademi619) ([@pedramkhademi619](https://github.com/pedramkhademi619)). If this project is useful to you, a ⭐ on the repo helps others find it.
