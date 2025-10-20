import requests
import json
from datetime import datetime, timedelta

CACHE_FILE = "exchange_rates.json"
CACHE_EXPIRY_HOURS = 24


def get_live_exchange_rates(base="NGN"):
    """Fetch latest exchange rates and convert to NGN-per-currency."""
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "rates" not in data:
            print("⚠️ Unexpected API response:", data)
            return None

        rates = data["rates"]

        # Convert to NGN per currency (1 foreign currency = how many NGN)
        ngn_per_currency = {}
        for currency, rate in rates.items():
            if rate and rate != 0:
                ngn_per_currency[currency] = 1 / rate

        ngn_per_currency["NGN"] = 1.0
        return ngn_per_currency

    except Exception as e:
        print(f"⚠️ Error fetching live rates: {e}")
        return None


def get_cached_exchange_rates():
    """Return cached rates if recent, else fetch new ones."""
    try:
        with open(CACHE_FILE, "r") as f:
            cached = json.load(f)

        timestamp = datetime.fromisoformat(cached["timestamp"])
        age = datetime.now() - timestamp

        # If cache is still valid (< 24 hours)
        if age < timedelta(hours=CACHE_EXPIRY_HOURS):
            print(f"📦 Using cached rates (age: {age.seconds // 3600}h)")
            return cached["rates"]
        else:
            print("🔄 Cache expired, fetching new rates...")

    except Exception:
        print("🆕 No valid cache found, fetching fresh rates...")

    # Fetch new data
    live_rates = get_live_exchange_rates()
    if live_rates:
        with open(CACHE_FILE, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "rates": live_rates
            }, f, indent=2)
        print("✅ New rates saved to cache.")
        return live_rates
    else:
        # Fall back to old cache if available
        try:
            with open(CACHE_FILE, "r") as f:
                cached = json.load(f)
                print("⚠️ Using last saved rates (API failed).")
                return cached["rates"]
        except Exception:
            print("❌ No cache available and API failed.")
            return None
