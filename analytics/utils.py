from urllib.parse import urlparse

def detect_source(referrer: str, current_host: str, user_agent: str = ""):
    if not referrer:
        return "direct"

    parsed = urlparse(referrer.lower())
    domain = parsed.netloc
    host = current_host.lower()

    # Same domain → direct
    if host in domain:
        return "direct"

    # Instagram
    if "instagram.com" in domain or "l.instagram.com" in domain:
        return "instagram"

    # LinkedIn (redirect domains too)
    if (
        "linkedin.com" in domain
        or "lnkd.in" in domain
        or "linktr.ee" in domain
    ):
        return "linkedin"

    # Google organic
    if "google." in domain:
        return "organic"

    # Other social networks
    SOCIAL_DOMAINS = [
        "facebook.com", "fb.com", "m.facebook.com",
        "tiktok.com", "twitter.com", "x.com",
        "youtube.com", "pinterest.com", "snapchat.com"
    ]
    if any(s in domain for s in SOCIAL_DOMAINS):
        return "social"

    return "referral"
