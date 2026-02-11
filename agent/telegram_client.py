"""
Format and send listing notifications via the Telegram Bot API.
Compact message in chat; full details as an attached text file.
"""

import html
import json
import urllib.request
from typing import Any


def _mins(val: float | None) -> str:
    if val is None:
        return "n/a"
    return f"{int(round(val))} min"


def build_listing_message(listing: dict[str, Any]) -> str:
    """Build a short Telegram message: main details + link. Kept compact for the chat."""
    address = listing.get("address") or "—"
    price_cold = listing.get("price_eur")
    price_warm = listing.get("price_warm_eur")
    rooms = listing.get("rooms")
    url = listing.get("url") or ""
    uni_walk = listing.get("dist_university_walk_mins")
    uni_transit = listing.get("dist_university_transit_mins")
    hbf_walk = listing.get("dist_hbf_walk_mins")
    hbf_transit = listing.get("dist_hbf_transit_mins")
    value = listing.get("value_score")

    safe_address = html.escape(str(address))
    parts = [
        f"🏠 <b>{safe_address}</b>",
        "",
        f"💰 Cold: {price_cold:.0f} €" if price_cold is not None else "💰 Cold: —",
        f"   Warm: {price_warm:.0f} €" if price_warm is not None else "   Warm: —",
        f"🛏 Rooms: {rooms}" if rooms is not None else "🛏 Rooms: —",
        "",
        "📍 Constructor Uni: walk " + _mins(uni_walk) + " · transit " + _mins(uni_transit),
        "📍 Bremen HBF:      walk " + _mins(hbf_walk) + " · transit " + _mins(hbf_transit),
    ]
    if value is not None:
        parts.append("")
        parts.append(f"⭐ Value score: {value:.1f}/1.0")
    if url:
        parts.append("")
        parts.append(url)

    return "\n".join(parts).strip()


def build_listing_details_file(listing: dict[str, Any]) -> str:
    """Build full-detail text for the attached file (description, vibe, scam, etc.)."""
    lines = [
        "LISTING DETAILS",
        "===============",
        "",
        "Address: " + str(listing.get("address") or "—"),
        "Cold rent (€/month): " + (f"{listing['price_eur']:.0f}" if listing.get("price_eur") is not None else "—"),
        "Warm rent (€/month): " + (f"{listing['price_warm_eur']:.0f}" if listing.get("price_warm_eur") is not None else "—"),
        "Rooms: " + str(listing.get("rooms") if listing.get("rooms") is not None else "—"),
        "",
        "Travel times",
        "------------",
        "To Constructor University: walk " + _mins(listing.get("dist_university_walk_mins")) + ", transit " + _mins(listing.get("dist_university_transit_mins")),
        "To Bremen HBF: walk " + _mins(listing.get("dist_hbf_walk_mins")) + ", transit " + _mins(listing.get("dist_hbf_transit_mins")),
        "",
        "Details (summary)",
        "----------------",
        str(listing.get("details") or "(none)"),
        "",
        "Description (English)",
        "--------------------",
        str(listing.get("description_en") or listing.get("description") or "(none)"),
        "",
        "Neighbourhood",
        "-------------",
        str(listing.get("neighbourhood_vibe") or "(none)"),
        "",
        "Scam assessment",
        "----------------",
        f"Score: {listing.get('scam_score')}" if listing.get("scam_score") is not None else "Score: —",
        "Flags: " + str(listing.get("scam_flags") or []),
        "Reasoning: " + str(listing.get("scam_reasoning") or "—"),
        "",
        "Value score: " + (f"{listing['value_score']:.2f}/1.0" if listing.get("value_score") is not None else "—"),
        "",
        "Link: " + str(listing.get("url") or "—"),
    ]
    return "\n".join(lines)


def send_listing_to_telegram(
    listing: dict[str, Any],
    token: str,
    chat_id: str,
) -> None:
    """
    Send the listing as a compact message plus an attached details file.
    Uses Telegram Bot API: sendMessage then sendDocument.
    Raises on API or network error.
    """
    base = f"https://api.telegram.org/bot{token}"
    message_text = build_listing_message(listing)
    file_content = build_listing_details_file(listing).encode("utf-8")
    filename = "listing_details.txt"

    # 1) Send message (HTML for bold/link)
    req = urllib.request.Request(
        f"{base}/sendMessage",
        data=json.dumps({
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode())
    if not out.get("ok"):
        raise RuntimeError("Telegram sendMessage failed: " + str(out.get("description", out)))

    # 2) Send document (multipart/form-data)
    boundary = "----EscaperFormBoundary" + str(abs(hash(filename)))
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'
        "Content-Type: text/plain; charset=utf-8\r\n\r\n"
    ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{base}/sendDocument",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode())
    if not out.get("ok"):
        raise RuntimeError("Telegram sendDocument failed: " + str(out.get("description", out)))
