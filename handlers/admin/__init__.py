from handlers.admin.menu import router as menu_router
from handlers.admin.today import router as today_router
from handlers.admin.clients import router as clients_router
from handlers.admin.offers import router as offers_router
from handlers.admin.leadforms import router as forms_router
from handlers.admin.questions import router as questions_router
from handlers.admin.referrals import router as refs_router
from handlers.admin.leads import router as leads_router
from handlers.admin.stats import router as stats_router
from handlers.admin.exports import router as exports_router
from handlers.admin.conversions import router as conversions_router
from handlers.admin.wizard import router as wizard_router
from handlers.admin.pixels import router as pixels_router

__all__ = [
    "menu_router",
    "today_router",
    "clients_router",
    "offers_router",
    "forms_router",
    "questions_router",
    "refs_router",
    "leads_router",
    "stats_router",
    "exports_router",
    "conversions_router",
    "wizard_router",
    "pixels_router",
]
