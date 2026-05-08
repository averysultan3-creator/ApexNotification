LEADGEN_FIELD = "leadgen"


def graph_lead_url(version: str, leadgen_id: str) -> str:
    return f"https://graph.facebook.com/{version}/{leadgen_id}"
