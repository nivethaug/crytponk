from typing import Optional
from services.api_client import (
    get_crypto_price,
    get_markets,
    get_top_coins,
    get_top_gainers,
    get_top_losers,
)
from utils.logger import logger
from models.user import User


# ============================================================================
# TELEGRAM MESSAGE LIMIT HELPER
# ============================================================================

def _split_response(text: str, max_chars: int = 3900) -> list:
    """
    Split a long response into chunks that fit within Telegram's 4096-char limit.
    Splits on double-newlines to preserve formatting.
    """
    chunks = []
    for block in text.split("\n\n"):
        if not chunks or len(chunks[-1]) + len(block) + 2 > max_chars:
            chunks.append(block)
        else:
            chunks[-1] += "\n\n" + block
    return chunks


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def _fmt_price(price) -> str:
    """Format a price with appropriate precision based on magnitude."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return "N/A"
    if p >= 1000:
        return f"${p:,.2f}"
    if p >= 1:
        return f"${p:,.4f}"
    if p >= 0.01:
        return f"${p:,.6f}"
    return f"${p:,.8f}".rstrip("0").rstrip(".")


def _fmt_change(change) -> str:
    """Format a 24h percentage change with arrow + color-less sign."""
    try:
        c = float(change)
    except (TypeError, ValueError):
        return "0.00%"
    arrow = "▲" if c >= 0 else "▼"
    return f"{arrow} {abs(c):.2f}%"


def _fmt_billion(value) -> str:
    """Format a large USD value (market cap / volume) compactly."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if v >= 1_000_000_000_000:
        return f"${v/1_000_000_000_000:.2f}T"
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"${v/1_000:.2f}K"
    return f"${v:,.2f}"


def _fmt_market_row(rank: int, coin: dict) -> str:
    """Format one coin as a single text row for /market, /gainers, /losers."""
    symbol = (coin.get("symbol") or "?").upper()
    name = coin.get("name") or symbol
    price = coin.get("current_price")
    change = coin.get("price_change_percentage_24h")
    mcap = coin.get("market_cap")

    line = f"{rank:>2}. *{name}* ({symbol})\n"
    line += f"    {_fmt_price(price)}   {_fmt_change(change)}"
    if mcap:
        line += f"   | MCap {_fmt_billion(mcap)}"
    return line


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def process_user_input(text: str, user: Optional[User] = None) -> str:
    text_lower = text.lower().strip()
    logger.info(f"Processing: {text_lower[:50]}")

    if not text_lower:
        return "⚠️ Please send a valid message."

    # =========================
    # DEFAULT COMMANDS
    # =========================

    if text_lower.startswith("/start") or text_lower == "start":
        return _handle_start(user)

    if text_lower.startswith("/help") or text_lower == "help":
        return _handle_help()

    if text_lower.startswith("/status") or text_lower == "status":
        return _handle_status(user)

    # /ask <question>
    if text_lower.startswith("/ask"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            return (
                "💡 Usage: /ask <your question>\n\n"
                "Examples:\n"
                "• /ask what is bitcoin?\n"
                "• /ask how does blockchain work?"
            )
        return _handle_ask(parts[1])

    # =========================
    # CRYPTO COMMANDS
    # =========================

    # /price <coin>
    if text_lower.startswith("/price") or text_lower.startswith("price "):
        parts = text_lower.split()
        if len(parts) < 2:
            return "💡 Usage: /price <coin>\nExample: /price btc"
        return _handle_crypto_query(parts[1])

    # /market [n]  - top N coins by market cap
    if text_lower.startswith("/market") or text_lower.startswith("/top"):
        parts = text_lower.split()
        limit = 10
        if len(parts) >= 2 and parts[1].isdigit():
            limit = min(int(parts[1]), 50)
        return _handle_market(limit)

    # /gainers [n]  - top gainers 24h
    if text_lower.startswith("/gainers") or text_lower.startswith("/gain"):
        parts = text_lower.split()
        limit = 10
        if len(parts) >= 2 and parts[1].isdigit():
            limit = min(int(parts[1]), 50)
        return _handle_gainers(limit)

    # /losers [n]  - top losers 24h
    if text_lower.startswith("/losers") or text_lower.startswith("/loser"):
        parts = text_lower.split()
        limit = 10
        if len(parts) >= 2 and parts[1].isdigit():
            limit = min(int(parts[1]), 50)
        return _handle_losers(limit)

    # =========================
    # NATURAL CRYPTO QUERIES
    # =========================

    # "market", "top coins", "top 10"
    if any(k in text_lower for k in ["market", "top coins", "top 10", "top crypto"]):
        return _handle_market(10)

    if "gainer" in text_lower or "pumping" in text_lower or "moon" in text_lower:
        return _handle_gainers(10)

    if "loser" in text_lower or "dumping" in text_lower or "crash" in text_lower:
        return _handle_losers(10)

    # Symbol / name shortcuts (e.g. "btc", "ethereum", "solana price")
    if any(k in text_lower for k in ["btc", "bitcoin"]):
        return _handle_crypto_query("bitcoin")

    if any(k in text_lower for k in ["eth", "ethereum"]):
        return _handle_crypto_query("ethereum")

    # =========================
    # GENERAL INTERACTIONS
    # =========================

    if any(word in text_lower for word in ["hello", "hi", "hey", "hola"]):
        if user and user.telegram_username:
            return f"👋 Hello @{user.telegram_username}! How can I help you today?"
        return "👋 Hello! How can I help you today?"

    if "whoami" in text_lower or "who am i" in text_lower:
        if user:
            return (
                f"🆔 Your Telegram ID: {user.telegram_user_id}\n"
                f"💬 Chat ID: {user.telegram_chat_id}\n"
                f"👤 Username: @{user.telegram_username or 'not set'}"
            )
        return "⚠️ User data not available"

    return _get_default_response()


# =========================
# HANDLERS
# =========================

def _handle_start(user: Optional[User]) -> str:
    name_part = ""
    if user and user.telegram_username:
        name_part = f" @{user.telegram_username}!"
    return (
        f"👋 Welcome{name_part}\n\n"
        "🪙 *Crypto Price Bot* is ready!\n\n"
        "*Commands:*\n"
        "• /price <coin> — Current price (e.g. /price btc)\n"
        "• /market [n] — Top N by market cap (default 10)\n"
        "• /gainers [n] — Top 24h gainers\n"
        "• /losers [n] — Top 24h losers\n"
        "• /ask <question>\n"
        "• /help\n\n"
        "*Natural queries also work:*\n"
        "• btc\n"
        "• market\n"
        "• gainers\n"
    )


def _handle_help() -> str:
    return (
        "📚 *Commands*\n\n"
        "• /price <coin> — Current price + 24h change\n"
        "  e.g. /price btc, /price eth, /price sol\n"
        "• /market [n] — Top N coins by market cap\n"
        "• /gainers [n] — Top gainers (24h)\n"
        "• /losers [n] — Top losers (24h)\n"
        "• /status — Bot status\n"
        "• /start — Welcome message\n\n"
        "*Try also:*\n"
        "• btc  /  eth\n"
        "• market  /  gainers  /  losers\n"
    )


def _handle_status(user: Optional[User]) -> str:
    import datetime
    return (
        "✅ Bot Online\n"
        f"🕐 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "🔌 Data source: CoinGecko"
    )


def _handle_ask(question: str) -> str:
    q_lower = question.lower()
    # Detect crypto intent and answer with live price
    for keyword, coin in [
        ("btc", "bitcoin"), ("bitcoin", "bitcoin"),
        ("eth", "ethereum"), ("ethereum", "ethereum"),
        ("sol", "solana"), ("solana", "solana"),
        ("bnb", "binancecoin"), ("xrp", "ripple"),
        ("ada", "cardano"), ("doge", "dogecoin"),
    ]:
        if keyword in q_lower:
            return _handle_crypto_query(coin)
    return (
        f"🤔 {question}\n\n"
        "⚠️ General AI not enabled yet.\n"
        "Try crypto commands like /price btc"
    )


# -------------------- CRYPTO HANDLERS --------------------

def _handle_crypto_query(coin: str) -> str:
    """Fetch and format a single coin's price + 24h stats."""
    result = get_crypto_price(coin_id=coin)

    if not result.get("success"):
        return (
            f"💰 {coin.upper()}: live price unavailable.\n\n"
            "⚠️ CoinGecko may be rate-limited. Try again shortly.\n"
            "Usage: /price <coin>  (e.g. btc, eth, sol)"
        )

    price = result["price"]
    change = result.get("change_24h", 0)
    volume = result.get("volume_24h", 0)
    mcap = result.get("market_cap", 0)

    arrow = "▲" if change >= 0 else "▼"
    sign = "+" if change >= 0 else ""

    lines = [
        f"💰 *{result['coin'].upper()}*",
        f"Price: {_fmt_price(price)}",
        f"24h: {arrow} {sign}{change:.2f}%",
    ]
    if mcap:
        lines.append(f"Market Cap: {_fmt_billion(mcap)}")
    if volume:
        lines.append(f"24h Volume: {_fmt_billion(volume)}")
    return "\n".join(lines)


def _handle_market(limit: int) -> str:
    """Top N coins by market cap."""
    result = get_top_coins(limit=limit)
    if not result.get("success"):
        return _market_fallback(limit, "market overview")

    coins = result.get("data", [])
    if not coins:
        return "⚠️ No market data returned. Try again later."

    header = f"📊 *Top {len(coins)} by Market Cap*\n"
    rows = [_fmt_market_row(i + 1, c) for i, c in enumerate(coins)]
    body = "\n".join(rows)
    return _safe_send(header + "\n" + body)


def _handle_gainers(limit: int) -> str:
    """Top N gainers over 24h."""
    result = get_top_gainers(limit=limit)
    if not result.get("success"):
        return _market_fallback(limit, "top gainers")

    coins = result.get("data", [])
    if not coins:
        return "⚠️ No gainer data returned. Try again later."

    header = f"🚀 *Top {len(coins)} Gainers (24h)*\n"
    rows = [_fmt_market_row(i + 1, c) for i, c in enumerate(coins)]
    body = "\n".join(rows)
    return _safe_send(header + "\n" + body)


def _handle_losers(limit: int) -> str:
    """Top N losers over 24h."""
    result = get_top_losers(limit=limit)
    if not result.get("success"):
        return _market_fallback(limit, "top losers")

    coins = result.get("data", [])
    if not coins:
        return "⚠️ No loser data returned. Try again later."

    header = f"📉 *Top {len(coins)} Losers (24h)*\n"
    rows = [_fmt_market_row(i + 1, c) for i, c in enumerate(coins)]
    body = "\n".join(rows)
    return _safe_send(header + "\n" + body)


def _safe_send(text: str) -> str:
    """
    process_user_input returns a single str. If the text would exceed Telegram's
    4096-char limit, we truncate and append a hint. The caller (handler) sends
    this single message.
    """
    if len(text) <= 3900:
        return text
    chunks = _split_response(text, max_chars=3900)
    # Return the first chunk with a continuation note.
    first = chunks[0]
    first += "\n\n… (list truncated, request a smaller N for full output)"
    return first


def _market_fallback(limit: int, what: str) -> str:
    return (
        f"⚠️ Could not fetch {what} (top {limit}).\n\n"
        "CoinGecko may be rate-limited or unreachable.\n"
        "Please try again in a few seconds.\n\n"
        "Tip: /market 5  (smaller list)"
    )


def _get_default_response() -> str:
    return (
        "🤖 I didn't understand.\n\n"
        "Try:\n"
        "• /price btc\n"
        "• /market\n"
        "• /gainers\n"
        "• /losers\n"
        "• /help"
    )
