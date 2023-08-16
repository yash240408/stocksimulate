import os
import matplotlib.pyplot as plt

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

API_KEY = "pk_c593f81a17d04c7598f2afc12ce9abd1"



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
    # Fetching the required details from transactions table
    values = db.execute(
        "SELECT symbol, name, price, SUM(shares) AS shares FROM transactions WHERE user_id = ? GROUP BY symbol", session["user_id"])
    # Fetching the available cash from users table
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    # Gives current value of cash
    total = cash
    # Value of shares na dcash get updated on every sell and buy
    for value in values:
        total += value["price"] * value["shares"]
    return render_template("index.html", values=values, cash=cash, usd=usd, total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        user_id = session["user_id"]
        symbol = request.form.get("symbol")
        share = request.form.get("shares")
        item = lookup(symbol)
        # Check if both are empty
        if symbol == "":
            return apology("Missing Symbol")
        elif not share.isdigit():
            return apology("Missing shares")
        elif share == "":
            return apology("Missing share"), 400
        elif share is None:
            return apology("Missing share")
        try:
            converted_share = int(share)
        except:
            return apology("Something went wrong"), 400
        if item is None:
            return apology("Invalid Symbol")
        # Retrive of available cash from users table
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        stock_name = item["name"]
        stock_price = int(item["price"])
        total_price = stock_price * converted_share
        # Condition checking
        if int(cash) < int(total_price):
            return apology("Not eneough cash available for buying"), 400
        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ? ", (cash - total_price), user_id)
            db.execute("INSERT INTO transactions(user_id, name, symbol, type, shares, price) VALUES(?, ?, ?, ?, ?, ?)",
                       user_id, stock_name, symbol, "BUY", converted_share, stock_price)
        return redirect("/")

    else:
        return render_template("buy.html"), 400


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    buy = db.execute("SELECT * FROM transactions WHERE user_id = ? AND type='BUY'", session["user_id"])
    sell = db.execute("SELECT * FROM transactions WHERE user_id = ? AND type='SELL'", session["user_id"])

    buy_graph={"time":[],"price":[]}
    sell_graph={"time":[],"price":[]}
    for i in buy:
        buy_graph["price"].append(i["price"])
        buy_graph["time"].append(i["timimg"])
    for i in sell:
        sell_graph["price"].append(i["price"])
        sell_graph["time"].append(i["timimg"])
    profit=[]
    time=[]
    for i in range(len(buy_graph["price"])):
        profit.append(sell_graph["price"][i]-buy_graph["price"][i])
        time.append(sell_graph["time"][i][11:16])
    for i in profit:
            fig, ax = plt.subplots()
            ax.barh(time, profit, align='center')
            plt.xlabel("Profit")
            plt.ylabel("Time")
            plt.savefig('./static/img/profit.jpg')
    return render_template("history.html", buy=buy, sell=sell, usd=usd)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide a username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide a password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("Invalid username or password", 403)

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
        stock = request.form.get("symbol")
        # Invalid input checking
        if stock == "":
            return apology("Invalid Symbol")
        item = lookup(stock)
        if item == None:
            return apology("Invalid Symbol")
        return render_template("quote.html", item=item, usd_function=usd)
    else:
        return render_template("quote.html"), 400


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        uname = request.form.get("username")
        upass = request.form.get("password")
        ucpass = request.form.get("confirmation")

        # User input validation
        if uname == "" and upass == "" and ucpass == "":
            return apology("Please fill all the details to process further")

        elif not uname:
            return apology("Username is required")

        elif not upass:
            return apology('Password is required')

        elif not ucpass:
            return apology('Confirm password is required')

        elif ucpass != upass:
            return apology('Both password must match')

        # Password generating process
        hash = generate_password_hash(upass)
        checks = db.execute("SELECT * FROM users")
        for check in checks:
            if uname in check["username"]:
                return apology(f'The username is not available kindly use another')
        try:
            db.execute("INSERT INTO users (username,hash) VALUES (?, ?)", uname, hash)
            return redirect("/")
        except:
            pass

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shareno = int(request.form.get("shares"))

        itemprice = lookup(symbol)["price"]
        itemname = lookup(symbol)["name"]
        total = shareno * itemprice

        own = db.execute("SELECT shares FROM transactions WHERE user_id = ? and symbol = ? GROUP BY symbol",
                         session["user_id"], symbol)[0]["shares"]

        if own < shareno:
            return apology("You don;t have eneough share to sell ")
        cash = db.execute("SELECT cash from users WHERE id = ?", session["user_id"])[0]["cash"]
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + total, session["user_id"])
        db.execute("INSERT INTO transactions(user_id, name, symbol, type, shares, price) VALUES(?, ?, ?, ?, ?, ?)",
                   session["user_id"], itemname, symbol, "SELL", -(shareno), itemprice)

        return redirect("/")
    else:
        values = db.execute("SELECT symbol, name, price, SUM(shares) AS shares FROM transactions WHERE user_id = ? GROUP BY symbol", session["user_id"])
        return render_template("sell.html", values=values)
