import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

os.environ["API_KEY"] = "pk_a645b86e64664d1cb24f8f527de5939c"

# Make sure API key is 
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]
    stocks = db.execute("SELECT symbol, name, price, SUM(shares) as total_shares FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    total = cash
    for stock in stocks:
        total += stock["total_shares"] * stock["price"]

    return render_template("index.html", stocks=stocks, cash=usd(cash), total=usd(total))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        item = lookup(symbol)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]


        if not symbol:
            return apology("Enter a symbol")
        elif not item:
            return apology("Invalid symbol")
        elif not shares:
            return apology("Input number of shares")

        item_name = item["Name"]
        shares = float(shares)
        item_price = float(item["Price"][:-1])
        total_price = item_price * shares

        if shares % 1 != 0:
            return apology("Shares must be an integer")
        elif shares < 0:
            return apology("You can't buy negative shares")
        elif cash < total_price:
            return apology("You can't afford that many shares")
        
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - total_price, user_id)
        db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", 
                    user_id, item_name, shares, item_price, "buy", symbol)
        
        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transactions = db.execute("SELECT symbol, price, shares, type, time FROM transactions WHERE user_id = ?", user_id)
    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        stock_info = lookup(request.form.get("symbol"))
        
        if not stock_info:
            return apology("Invalid symbol")
        
        return render_template("quote_results.html", stock_info=stock_info)


    else:
        return render_template("quote_search.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Ensure password confirmation was submitted
        elif not request.form.get("confirm_password"):
            return apology("must provide password confirmation", 403)
        
        # Ensure passwords match
        elif request.form.get("confirm_password") != request.form.get("password"):
            return apology("passwords don't match", 403)


        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username is available
        if len(rows) > 0:
            return apology("username is not available", 403)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"), generate_password_hash(request.form.get("password")))

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]

    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")


        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        if symbol == "Symbol":
            return apology("enter a symbol")
        elif not shares:
            return apology("Input number of shares")
        
        symbol = symbol.upper()

        shares = float(shares)
        total_shares = db.execute("SELECT SUM(shares) FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", user_id, symbol)[0]["SUM(shares)"]
        item = lookup(symbol)

        item_name = item["Name"]
        item_price = float(item["Price"][:-1])
        total_price = item_price * shares

        if shares % 1 != 0:
            return apology("Shares must be an integer")
        elif shares < 0:
            return apology("You can't sell negative shares")
        elif shares > total_shares:
            return apology("You you don't have that many shares")
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + total_price, user_id)
        db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", 
                    user_id, item_name, -shares, item_price, "sell", symbol)
        
        return redirect("/")

    else:
        stocks = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
        return render_template("sell.html", stocks=stocks)
