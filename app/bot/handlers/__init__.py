from app.bot.handlers.clients import router as clients_router
from app.bot.handlers.delivery_rules import router as delivery_rules_router
from app.bot.handlers.facebook_forms import router as facebook_forms_router
from app.bot.handlers.leads import router as leads_router
from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.prelands import router as prelands_router
from app.bot.handlers.settings import router as settings_router
from app.bot.handlers.stats import router as stats_router

routers = [
    menu_router,
    leads_router,
    facebook_forms_router,
    clients_router,
    delivery_rules_router,
    prelands_router,
    stats_router,
    settings_router,
]

__all__ = ["routers"]
