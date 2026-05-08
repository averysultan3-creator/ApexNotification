"""facebook.py — Facebook Graph API helpers."""
import logging
from typing import Any, Dict, Optional

import httpx

import config

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v19.0"


async def get_lead_details(leadgen_id: str) -> Optional[Dict[str, Any]]:
    if not config.FACEBOOK_PAGE_ACCESS_TOKEN:
        return None
    url = f"{GRAPH_BASE}/{leadgen_id}"
    params = {
        "fields": "field_data,created_time,ad_id,form_id,page_id",
        "access_token": config.FACEBOOK_PAGE_ACCESS_TOKEN,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.error("Graph API error for leadgen_id=%s: %s", leadgen_id, exc)
        return None
