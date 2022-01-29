import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)
        response.raise_for_status()
        print(response)
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        if quote["isUSMarketOpen"]:
            market_state = "Open"
        else:
            market_state = "Closed"
        return {
            "Name": quote["companyName"],
            "Price": str(float(quote["latestPrice"])) + "$",
            "Symbol": quote["symbol"],
            "Volume": str(quote["volume"]) + "$",
            "Market Cap": str(quote["marketCap"]) + "$",
            "Last Close Price": str(quote["previousClose"]) + "$",
            "Today change": str(round(float(quote["changePercent"]), 2)) + "%",
            "Yearly high": str(quote["week52High"]) + "$",
            "Yearly low": str(quote["week52Low"]) + "$",
            "Yearly Change": str(round(float(quote["ytdChange"]), 2)) + "%",
            "US Market State": market_state
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
