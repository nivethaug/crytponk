"""
API Client module.
ALL external API calls go here.
Easy to modify by AI agents.

# DreamAgent: AI can add helper functions here for dynamic integrations
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.logger import logger
from config import API_TIMEOUT


# ============================================================================
# SYMBOL -> COINGECKO ID MAP (for /price BTC style lookups)
# ============================================================================

SYMBOL_TO_ID = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "usdt": "tether", "tether": "tether",
    "bnb": "binancecoin", "binance": "binancecoin",
    "sol": "solana", "solana": "solana",
    "usdc": "usd-coin",
    "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "avax": "avalanche-2", "avalanche": "avalanche-2",
    "dot": "polkadot", "polkadot": "polkadot",
    "trx": "tron", "tron": "tron",
    "matic": "matic-network", "polygon": "matic-network",
    "link": "chainlink", "chainlink": "chainlink",
    "ltc": "litecoin", "litecoin": "litecoin",
    "shib": "shiba-inu", "shiba": "shiba-inu",
    "uni": "uniswap", "uniswap": "uniswap",
    "atom": "cosmos", "cosmos": "cosmos",
    "xlm": "stellar", "stellar": "stellar",
    "etc": "ethereum-classic",
    "near": "near",
    "apt": "aptos", "aptos": "aptos",
    "fil": "filecoin", "filecoin": "filecoin",
    "icp": "internet-computer",
    "hbar": "hedera-hashgraph",
    "arb": "arbitrum", "arbitrum": "arbitrum",
    "op": "optimism", "optimism": "optimism",
    "aave": "aave",
    "mkr": "maker", "maker": "maker",
    "inj": "injective-protocol",
    "tia": "celestia",
    "sui": "sui",
    "sei": "sei-network",
    "pepe": "pepe",
    "rndr": "render-token", "render": "render-token",
    "ftm": "fantom", "fantom": "fantom",
    "algo": "algorand", "algorand": "algorand",
    "vet": "vechain", "vechain": "vechain",
    "grt": "the-graph",
    "sand": "the-sandbox",
    "mana": "decentraland",
    "axs": "axie-infinity",
    "egld": "elrond-erd-2",
    "flow": "flow",
    "theta": "theta-token",
    "xtz": "tezos",
    "eos": "eos",
    "bch": "bitcoin-cash",
    "xmr": "monero",
    "dash": "dash",
    "zil": "zilliqa",
    "ctxc": "cortex",
    "dai": "dai",
    "busd": "binance-usd",
}


def resolve_coin_id(symbol: str) -> str:
    """Resolve a symbol or name (e.g. 'BTC' or 'bitcoin') to a CoinGecko coin id."""
    if not symbol:
        return ""
    s = symbol.lower().strip()
    if s in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[s]
    # Assume already a valid CoinGecko id
    return s


# ============================================================================
# UTILITY FUNCTIONS (Do not modify)
# ============================================================================

def fetch_json(url: str, params: dict = None, timeout: int = API_TIMEOUT) -> dict:
    """
    Generic JSON fetcher for public APIs.

    Args:
        url: API endpoint URL
        params: Optional query parameters
        timeout: Request timeout in seconds

    Returns:
        dict with success status and data or error
    """
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.Timeout:
        logger.error(f"API timeout: {url}")
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"success": False, "error": "Failed to fetch data"}


def safe_get(data: dict, *keys, default=None):
    """
    Safely get nested dictionary value.
    """
    for key in keys:
        try:
            data = data[key]
        except (KeyError, TypeError):
            return default
    return data


# ============================================================================
# CRYPTO API HELPERS (CoinGecko)
# ============================================================================

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def get_crypto_price(coin_id: str = "bitcoin", currency: str = "usd") -> dict:
    """
    Fetch cryptocurrency price + 24h change + market cap + volume from CoinGecko.

    Args:
        coin_id: Coin identifier (e.g., 'bitcoin', 'ethereum') or symbol ('btc')
        currency: Target currency (e.g., 'usd', 'eur')

    Returns:
        dict with price data or error info
    """
    # Resolve symbol -> id
    resolved = resolve_coin_id(coin_id)
    try:
        url = f"{COINGECKO_BASE}/simple/price"
        params = {
            "ids": resolved,
            "vs_currencies": currency,
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
            "include_market_cap": "true",
            "include_last_updated_at": "true",
        }

        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if resolved in data and currency in data[resolved]:
            coin_data = data[resolved]
            return {
                "success": True,
                "price": coin_data.get(currency, 0),
                "change_24h": coin_data.get(f"{currency}_24h_change", 0),
                "volume_24h": coin_data.get(f"{currency}_24h_vol", 0),
                "market_cap": coin_data.get(f"{currency}_market_cap", 0),
                "coin": resolved,
                "currency": currency,
                "last_updated": coin_data.get("last_updated_at"),
            }
        else:
            return {"success": False, "error": f"Coin '{coin_id}' not found"}
    except requests.exceptions.Timeout:
        logger.error(f"API timeout for {coin_id}")
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"API error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_crypto_price: {e}")
        return {"success": False, "error": "Failed to fetch data"}


def get_markets(limit: int = 10, order: str = "market_cap_desc") -> dict:
    """
    Fetch top cryptocurrency market data from CoinGecko /coins/markets.
    A single call returns price, 24h change, market cap, volume — enough for
    /market, /gainers, /losers and /price (by symbol).

    Args:
        limit: Number of coins to fetch (max 250)
        order: Sort order (market_cap_desc, market_cap_asc, volume_desc, etc.)

    Returns:
        dict with success status and a list of coin market dicts.
    """
    limit = max(1, min(int(limit), 250))
    try:
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": order,
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h",
        }
        response = requests.get(url, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list):
            return {"success": True, "data": data, "count": len(data)}
        return {"success": False, "error": "Unexpected response format"}
    except requests.exceptions.Timeout:
        logger.error("API timeout in get_markets")
        return {"success": False, "error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        logger.error(f"API error in get_markets: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error in get_markets: {e}")
        return {"success": False, "error": "Failed to fetch data"}


def get_top_coins(limit: int = 10) -> dict:
    """Fetch top N coins by market cap. Alias for get_markets(market_cap_desc)."""
    return get_markets(limit=limit, order="market_cap_desc")


def get_top_gainers(limit: int = 10) -> dict:
    """
    Fetch top gainers over 24h.
    Pulls the top 100 coins by market cap, then sorts by 24h % change desc.
    """
    market = get_markets(limit=100, order="market_cap_desc")
    if not market.get("success"):
        return market
    coins = market["data"]
    gainers = sorted(
        coins,
        key=lambda c: c.get("price_change_percentage_24h") if c.get("price_change_percentage_24h") is not None else -999,
        reverse=True,
    )
    return {"success": True, "data": gainers[:limit], "count": min(limit, len(gainers))}


def get_top_losers(limit: int = 10) -> dict:
    """
    Fetch top losers over 24h.
    Pulls the top 100 coins by market cap, then sorts by 24h % change asc.
    """
    market = get_markets(limit=100, order="market_cap_desc")
    if not market.get("success"):
        return market
    coins = market["data"]
    losers = sorted(
        coins,
        key=lambda c: c.get("price_change_percentage_24h") if c.get("price_change_percentage_24h") is not None else 999,
    )
    return {"success": True, "data": losers[:limit], "count": min(limit, len(losers))}


def get_weather(city: str) -> dict:
    """Fetch weather data (placeholder for future implementation)."""
    logger.info(f"Weather request for {city} - not implemented")
    return {"success": False, "error": "Weather API not configured yet"}


# ============================================================================
# CONCURRENT FETCH HELPER (use when multiple independent HTTP calls are needed)
# ============================================================================

def fetch_many(func, items, max_workers: int = 10):
    """
    Call `func` concurrently for each item in `items`.
    Returns a list of non-None results in completion order.

    Example:
        prices = fetch_many(get_crypto_price, ["bitcoin", "ethereum", "solana"])
    """
    results = []
    if not items:
        return results
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(func, item): item for item in items}
        for future in as_completed(futures):
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception as e:
                logger.error(f"fetch_many error: {e}")
    return results


# ============================================================================
# WEB SCRAPER USAGE EXAMPLE (Commented)
# ============================================================================

# The web_scraper.py module provides Chrome DevTools Protocol (CDP) scraping
# capabilities. Here's how to use it in your bot:
#
# from services.web_scraper import WebScraper, ScrapeConfig, scrape_url
# from services.web_scraper import register_scraper, get_scraper
#
# Example: simple scrape
# def scrape_example_site(url: str) -> dict:
#     config = ScrapeConfig(
#         url=url,
#         items_selector=".article",
#         fields={"title": "h2", "link": "a", "summary": ".summary"},
#         max_pages=5,
#         scroll=True
#     )
#     result = scrape_url(url, config)
#     return {"success": len(result.errors) == 0, "data": result.data, "errors": result.errors}
