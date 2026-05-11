# Apex Lead Router

Backend + Telegram bot for routing leads from Facebook Lead Forms, Google Sheets
Apps Script, and preland tracking into client Telegram recipients, archive, and
basic statistics.

## Current Flow

```text
Facebook Lead Form / Google Apps Script / Preland
-> FastAPI backend
-> SQLite database
-> Telegram client recipients
-> Archive and statistics
```

## Main Entities

- `FunnelForm` - one lead source/funnel with `fb_form_id`, join code, optional Google Sheet settings.
- `ClientRecipient` - Telegram user attached to one funnel.
- `Lead` - normalized lead row.
- `LeadDeliveryHistory` - per-recipient Telegram delivery status.
- `Preland` - tracked landing/prelanding page.
- `PrelandEvent` - `page_view` and `button_click` events.

## Project Structure

```text
app/
  bot/
    handlers/
    keyboards/
    states/
  web/
    api.py
    facebook_webhook.py
    funnel_webhook.py
    google_sheet_lead.py
    preland_tracking.py
    health.py
  models/
  services/
  utils/
alembic/
main.py
config.py
database.py
requirements.txt
.env.example
```

## Environment

Copy `.env.example` to `.env` and fill real values:

```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789
BOT_USERNAME=your_bot_username_without_at

DATABASE_URL=sqlite+aiosqlite:///./apex_lead_router.db

PUBLIC_BASE_URL=https://your-domain.com
WEB_HOST=0.0.0.0
WEB_PORT=8000

FACEBOOK_VERIFY_TOKEN=change_me_verify_token
FACEBOOK_APP_SECRET=
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token

GOOGLE_SERVICE_ACCOUNT_JSON=
```

`.env` is read as `utf-8-sig`, so UTF-8 BOM does not break config parsing.

## Run

```bat
SETUP_SERVER.bat
START_SERVER.bat
```

Manual modes:

```bat
python main.py web
python main.py bot
python main.py all
```

`all` runs Telegram polling and FastAPI together. `web` is useful for backend
checks without Telegram polling.

## Endpoints

```text
GET  /health
GET  /webhooks/facebook
POST /webhooks/facebook
GET  /track/pixel.js?pl=PRELAND_SLUG
POST /track/page-view
POST /track/button-click
POST /api/google-sheet/lead
```

## Facebook Setup

1. Create a funnel in the Telegram admin bot.
2. Put the Facebook Form ID into the funnel.
3. Configure Meta Webhooks callback:

```text
https://YOUR_DOMAIN/webhooks/facebook
```

4. Use the same verify token as `FACEBOOK_VERIFY_TOKEN`.
5. Subscribe to `leadgen`.
6. Add `FACEBOOK_PAGE_ACCESS_TOKEN` to `.env`.
7. Join client recipients through the generated Telegram join link.
8. Send a Meta test lead.

## Google Sheet Bridge

The Telegram admin bot can generate a full Apps Script for a funnel. The script
contains:

- `BACKEND_URL`
- `BACKEND_HEALTH_URL`
- `FUNNEL_ID`
- `SECRET`
- `FB_FORM_ID`
- `SHEET_NAME`
- `setup`
- `testConnection`
- `sendTestLead`
- duplicate protection through `SENT_IDS`

Backend endpoint:

```text
POST /api/google-sheet/lead
```

## Preland Tracking

Insert the generated pixel script before `</body>`:

```html
<script src="https://YOUR_DOMAIN/track/pixel.js?pl=remote-ua"></script>
```

Track CTA clicks with:

```html
<a href="https://t.me/your_bot_or_link" data-track-click="main_cta">
  Send request
</a>
```

The backend stores `page_view`, `button_click`, `utm_source`, and
`utm_campaign`. Bot statistics show visits, clicks, and CTR.

## Database

Apply migrations:

```bat
python -m alembic upgrade head
```

Current head: `011`.

The live schema should contain only:

```text
client_recipients
funnel_forms
lead_delivery_history
leads
preland_events
prelands
```

## Checks

```bat
python -m compileall -q app tests alembic main.py config.py database.py
python -m alembic heads
python -m alembic upgrade head
python -m pytest -q
```

## Windows Scripts

- `SETUP_SERVER.bat` - creates venv, installs requirements, creates `.env` from `.env.example` without BOM if missing, creates folders, runs migrations.
- `START_SERVER.bat` - starts `python -u main.py all`, writes logs through the app, checks `/health`, and avoids duplicate PID startup.
- `STOP_SERVER.bat` - stops the PID from `runtime/server.pid`.
- `RESTART_SERVER.bat` - stop then start.
- `WATCHDOG.bat` - checks `/health` and calls `START_SERVER.bat` when backend is down.
- `RUN.bat` - setup then start.
