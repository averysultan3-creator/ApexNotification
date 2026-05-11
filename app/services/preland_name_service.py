"""Smart preland name parser.

Admin can type anything like:
  "убер польша сторис девушки"
  "uberland pl reels men driver"
  "cz feed broad work"

Bot will generate:
  display_name: "Убер | PL | Story | Girls"
  slug:         "uber_pl_story_girls_001"
"""
from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

_TRANSLIT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

_COUNTRY_MAP: dict[str, str] = {
    # Russian
    "польша": "PL", "польши": "PL", "польшу": "PL",
    "чехия": "CZ", "чехии": "CZ", "чехию": "CZ",
    "германия": "DE", "германии": "DE",
    "нидерланды": "NL", "голландия": "NL",
    "румыния": "RO",
    "венгрия": "HU",
    "словакия": "SK",
    "австрия": "AT",
    "украина": "UA",
    "беларусь": "BY", "белоруссия": "BY",
    "литва": "LT", "латвия": "LV", "эстония": "EE",
    "франция": "FR", "испания": "ES", "италия": "IT",
    "португалия": "PT", "швеция": "SE", "норвегия": "NO",
    "дания": "DK", "финляндия": "FI", "греция": "GR", "болгария": "BG",
    "сербия": "RS", "хорватия": "HR", "словения": "SI",
    "бельгия": "BE", "швейцария": "CH",
    # English / codes
    "poland": "PL", "pl": "PL",
    "czech": "CZ", "cz": "CZ", "czechia": "CZ",
    "germany": "DE", "de": "DE",
    "netherlands": "NL", "nl": "NL", "holland": "NL",
    "romania": "RO", "ro": "RO",
    "hungary": "HU", "hu": "HU",
    "slovakia": "SK", "sk": "SK",
    "austria": "AT", "at": "AT",
    "ukraine": "UA", "ua": "UA",
    "belarus": "BY", "by": "BY",
    "lithuania": "LT", "lt": "LT",
    "latvia": "LV", "lv": "LV",
    "estonia": "EE", "ee": "EE",
    "france": "FR", "fr": "FR",
    "spain": "ES", "es": "ES",
    "italy": "IT", "it": "IT",
    "portugal": "PT", "pt": "PT",
    "sweden": "SE", "se": "SE",
    "norway": "NO", "no": "NO",
    "denmark": "DK", "dk": "DK",
    "finland": "FI", "fi": "FI",
    "greece": "GR", "gr": "GR",
    "bulgaria": "BG", "bg": "BG",
    "serbia": "RS", "rs": "RS",
    "croatia": "HR", "hr": "HR",
    "slovenia": "SI", "si": "SI",
    "belgium": "BE", "be": "BE",
    "switzerland": "CH", "ch": "CH",
    "usa": "US", "us": "US", "america": "US",
    "uk": "GB", "gb": "GB",
}

_PLACEMENT_MAP: dict[str, str] = {
    "сторис": "Story", "сторіс": "Story", "stories": "Story", "story": "Story",
    "рилс": "Reels", "рілс": "Reels", "reels": "Reels", "reel": "Reels",
    "фид": "Feed", "feed": "Feed",
    "поиск": "Search", "search": "Search",
    "видео": "Video", "video": "Video",
    "карусель": "Carousel", "carousel": "Carousel",
    "баннер": "Banner", "banner": "Banner",
    "инбокс": "Inbox", "inbox": "Inbox",
    "мессенджер": "Messenger", "messenger": "Messenger",
    "ретаргет": "Retarget", "retarget": "Retarget", "rtg": "Retarget",
}

_AUDIENCE_MAP: dict[str, str] = {
    "девушки": "Girls", "девушка": "Girls", "girls": "Girls", "girl": "Girls",
    "женщины": "Women", "женщин": "Women", "women": "Women", "woman": "Women",
    "мужчины": "Men", "мужчин": "Men", "парни": "Men", "men": "Men", "man": "Men",
    "широкая": "Broad", "широкий": "Broad", "широко": "Broad", "broad": "Broad",
    "диаспора": "Diaspora", "diaspora": "Diaspora",
    "молодые": "Young", "молодёжь": "Young", "молодежь": "Young", "young": "Young",
    "lookalike": "LAL", "lal": "LAL", "лал": "LAL",
    "18-35": "18-35", "25-40": "25-40", "25-45": "25-45", "18-24": "18-24",
    "18+": "18+", "25+": "25+",
    "укр": "UA",
}

# Maps display value → slug fragment
_SLUG_OVERRIDE: dict[str, str] = {
    "Story": "story", "Reels": "reels", "Feed": "feed", "Search": "search",
    "Video": "video", "Carousel": "carousel", "Banner": "banner",
    "Girls": "girls", "Women": "women", "Men": "men", "Broad": "broad",
    "Diaspora": "diaspora", "Young": "young", "Retarget": "rtg",
    "LAL": "lal", "Inbox": "inbox", "Messenger": "msgr",
    "18-35": "1835", "25-40": "2540", "25-45": "2545", "18-24": "1824",
    "18+": "18p", "25+": "25p",
}

_ALL_MAPS = [_COUNTRY_MAP, _PLACEMENT_MAP, _AUDIENCE_MAP]


@dataclass
class ParsedPreland:
    display_name: str
    slug_base: str


def _transliterate(text: str) -> str:
    out: list[str] = []
    for ch in text.lower():
        out.append(_TRANSLIT.get(ch, ch))
    return "".join(out)


def _display_to_slug(display_val: str) -> str:
    if display_val in _SLUG_OVERRIDE:
        return _SLUG_OVERRIDE[display_val]
    # Country code (2-3 uppercase letters) → lowercase
    if re.fullmatch(r"[A-Z]{2,3}", display_val):
        return display_val.lower()
    # Multi-word: "UA Diaspora" → "ua_diaspora"
    parts = display_val.lower().split()
    frag = "_".join(re.sub(r"[^a-z0-9]", "", p) for p in parts)
    return frag.strip("_") or "x"


def parse_preland_input(text: str) -> ParsedPreland:
    """Convert free-form admin input to structured ParsedPreland."""
    # Split by any separator: space, pipe, comma, slash
    words = re.split(r"[\s|,/\\]+", text.strip())
    words = [w.strip() for w in words if w.strip()]

    display_parts: list[str] = []
    slug_parts: list[str] = []

    for word in words:
        w_lower = word.lower()
        matched_display = None

        for m in _ALL_MAPS:
            if w_lower in m:
                matched_display = m[w_lower]
                break

        if matched_display is not None:
            display_parts.append(matched_display)
            slug_parts.append(_display_to_slug(matched_display))
        else:
            # Transliterate if contains Cyrillic
            if any(ch in _TRANSLIT for ch in w_lower):
                trans = _transliterate(w_lower)
            else:
                trans = w_lower
            slug_frag = re.sub(r"[^a-z0-9]", "", trans)[:12]
            if slug_frag:
                # Capitalize first letter of original for display
                display_parts.append(word[0].upper() + word[1:] if word else word)
                slug_parts.append(slug_frag)

    if not display_parts:
        raw = text.strip()[:60]
        trans = _transliterate(raw.lower())
        slug_frag = re.sub(r"[^a-z0-9]", "", trans)[:30] or "preland"
        return ParsedPreland(display_name=raw, slug_base=slug_frag)

    display_name = " | ".join(display_parts)
    slug_base = "_".join(p for p in slug_parts if p)[:50]
    return ParsedPreland(display_name=display_name, slug_base=slug_base or "preland")


async def generate_unique_slug(session, slug_base: str) -> str:
    """Return unique slug like uber_pl_story_girls_001."""
    from app.services.preland_service import get_preland_by_slug
    for i in range(1, 999):
        candidate = f"{slug_base}_{i:03d}"
        if not await get_preland_by_slug(session, candidate):
            return candidate
    return f"{slug_base}_{secrets.token_hex(3)}"
