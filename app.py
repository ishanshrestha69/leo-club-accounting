from flask import Flask, render_template, request, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "leo_secret_key"

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///leo.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------ DATABASE MODELS ------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    source = db.Column(db.String(100))
    amount = db.Column(db.Float)
    receipt_number = db.Column(db.String(50))

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    expense_type = db.Column(db.String(100))
    amount = db.Column(db.Float)
    voucher_number = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect("/dashboard")
    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    total_income = sum([i.amount for i in Income.query.all()])
    total_expense = sum([e.amount for e in Expense.query.all()])
    balance = total_income - total_expense
    return render_template("dashboard.html",
                           income=total_income,
                           expense=total_expense,
                           balance=balance)

@app.route("/add_income", methods=["POST"])
@login_required
def add_income():
    year = datetime.now().year
    count = Income.query.count() + 1
    receipt = f"LC-INC-{year}-{count:04d}"

    income = Income(
        date=request.form["date"],
        source=request.form["source"],
        amount=float(request.form["amount"]),
        receipt_number=receipt
    )
    db.session.add(income)
    db.session.commit()
    return redirect("/dashboard")

@app.route("/add_expense", methods=["POST"])
@login_required
def add_expense():
    year = datetime.now().year
    count = Expense.query.count() + 1
    voucher = f"LC-EXP-{year}-{count:04d}"

    expense = Expense(
        date=request.form["date"],
        expense_type=request.form["type"],
        amount=float(request.form["amount"]),
        voucher_number=voucher
    )
    db.session.add(expense)
    db.session.commit()
    return redirect("/dashboard")

@app.route("/export")
@login_required
def export_excel():
    data = [{
        "Date": i.date,
        "Source": i.source,
        "Amount": i.amount,
        "Receipt": i.receipt_number
    } for i in Income.query.all()]

    df = pd.DataFrame(data)
    filename = "income.xlsx"
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not User.query.first():
            admin = User(username="treasurer", password="1234", role="Treasurer")
            viewer = User(username="viewer", password="1234", role="Viewer")
            db.session.add(admin)
            db.session.add(viewer)
            db.session.commit()
    app.run(debug=True)
