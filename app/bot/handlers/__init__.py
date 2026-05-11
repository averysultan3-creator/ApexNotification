from app.bot.handlers.client import router as client_router
from app.bot.handlers.funnel import router as funnel_router
from app.bot.handlers.leads import router as leads_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.prelands import router as prelands_router
from app.bot.handlers.stats import router as stats_router
from app.bot.handlers.settings import router as settings_router

routers = [
    menu_router,      # must be first (handles /start)
    client_router,    # client cabinet — before admin handlers
    funnel_router,
    leads_router,
    prelands_router,
    stats_router,
    settings_router,
]

__all__ = ["routers"]
