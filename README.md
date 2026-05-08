# Apex Lead Router

Simple router for Facebook Lead Forms and GitHub Pages prelands.

No CRM cabinet, roles, funnels, pixel manager, tariffs, or drop-off analytics. The app only does this:

- receives Facebook Lead Ads webhooks
- maps Facebook forms to clients
- delivers leads to admin Telegram, client Telegram IDs, email, and optional Google Sheet target
- tracks preland `page_view` and `button_click`
- shows basic Telegram admin statistics

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
    preland_tracking.py
    health.py
  models/
  services/
  utils/
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
FACEBOOK_APP_SECRET=your_facebook_app_secret
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token
```

## Run

```bat
python main.py bot
python main.py web
python main.py all
```

`all` runs Telegram polling and FastAPI together. `web` is useful when you run the bot elsewhere.

## Endpoints

```text
GET  /health
GET  /webhooks/facebook
POST /webhooks/facebook
GET  /track/pixel.js?pl=PRELAND_SLUG
POST /track/page-view
POST /track/button-click
```

## Facebook Setup

1. Create a Meta App.
2. Add Webhooks product.
3. Select Page object.
4. Use callback URL:

```text
https://YOUR_DOMAIN/webhooks/facebook
```

5. Use the same verify token as `FACEBOOK_VERIFY_TOKEN`.
6. Subscribe to `leadgen`.
7. Give the app access to the Facebook Page.
8. Get a Page Access Token.
9. Put the token into `.env` as `FACEBOOK_PAGE_ACCESS_TOKEN`.
10. In Telegram bot, add FB Page ID and FB Form ID.
11. Create a delivery rule.
12. Send a test lead.

## Preland Setup

For a GitHub Pages preland, insert before `</body>`:

```html
<script src="https://YOUR_DOMAIN/track/pixel.js?pl=remote-ua"></script>
```

On each CTA:

```html
<a href="https://t.me/your_bot_or_link" data-track-click="main_cta">
  Оставить заявку
</a>
```

The bot will count:

```text
page_view
button_click: main_cta
CTR = clicks / visits * 100
```

## Telegram Menu

```text
🏠 Apex Lead Router

[📥 Лиды] [📋 FB Формы]
[👥 Клиенты] [🔀 Правила]
[🌐 Prelands] [📊 Статистика]
[⚙️ Настройки]
```

## Database

Apply migrations:

```bat
python -m alembic upgrade head
```

Revision `005` replaces the older CRM/funnel schema with the simplified Apex Lead Router tables.

## Checks

```bat
python -m pytest tests/ -v
```

PowerShell compile check:

```powershell
Get-ChildItem -Recurse -Filter "*.py" | Where-Object { $_.FullName -notmatch "__pycache__" } | ForEach-Object { python -m py_compile $_.FullName }
```

## Manual Checklist

```text
[ ] /start opens Apex Lead Router
[ ] Created client
[ ] Added client Telegram ID
[ ] Added client email
[ ] Added FB form
[ ] Created delivery rule
[ ] Sent test lead
[ ] Lead arrived to admin
[ ] Lead arrived to client
[ ] Lead saved in DB
[ ] DeliveryLog saved
[ ] Created preland
[ ] Got tracking code
[ ] Inserted JS into GitHub Pages preland
[ ] Added data-track-click to CTA
[ ] Opened preland
[ ] Clicked CTA
[ ] Telegram shows visits/clicks/CTR
[ ] Checked /health
[ ] Checked Facebook webhook verify
```
