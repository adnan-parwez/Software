import json
import csv
from datetime import datetime
from config import *

def fmt(val):
    try:
        v = float(val)
        return str(int(v)) if v == int(v) else f"{v:.2f}"
    except Exception:
        return str(val)

def get_next_bill_number():
    today_key = datetime.now().strftime("%d%m%y")
    try:
        with open(BILL_COUNTER_FILE, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    if data.get('date') != today_key:
        data = {'date': today_key, 'last': 0}
    data['last'] += 1
    with open(BILL_COUNTER_FILE, 'w') as f:
        json.dump(data, f)
    return f"{today_key}{data['last']:02d}"

def load_products():
    data = {}
    try:
        with open("products.csv", newline="", encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                data[r["code"]] = {
                    "name": r["name"],
                    "mrp": float(r["mrp"]),
                    "price": float(r["price"]),
                    "stock": float(r["stock"]),
                }
    except FileNotFoundError:
        data = create_default_products()
    return data

def create_default_products():
    d = {
        "1001": {"name": "Rice (1kg)", "mrp": 55.0, "price": 50.0, "stock": 100},
        "1002": {"name": "Honey (500g)", "mrp": 400.0, "price": 350.0, "stock": 10},
        "1003": {"name": "Biscuit", "mrp": 35.0, "price": 30.0, "stock": 100},
    }
    save_products(d)
    return d

def save_products(products):
    with open("products.csv", "w", newline="", encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "mrp", "price", "stock"])
        for c, p in products.items():
            w.writerow([c, p["name"], p["mrp"], p["price"], p["stock"]])

def load_customers():
    customers = {}
    try:
        with open("customers.csv", newline="", encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                customers[r["phone"]] = {
                    "name": r["name"],
                    "points": int(float(r["points"])),
                    "gifts": int(float(r.get("gifts", 0))),
                    "gift_name": r.get("gift_name", "")
                }
    except FileNotFoundError:
        with open("customers.csv", "w", newline="", encoding='utf-8') as f:
            csv.writer(f).writerow(["phone", "name", "points", "gifts", "gift_name"])
    return customers

def save_customers(customers):
    with open("customers.csv", "w", newline="", encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["phone", "name", "points", "gifts", "gift_name"])
        for phone, d in customers.items():
            w.writerow([phone, d["name"], d["points"], d.get("gifts", 0), d.get("gift_name", "")])

def load_dues():
    try:
        with open("dues.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_dues(dues):
    with open("dues.json", "w") as f:
        json.dump(dues, f, indent=2)

def load_purchases():
    try:
        with open(PURCHASES_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_purchases(p):
    with open(PURCHASES_FILE, "w") as f:
        json.dump(p, f, indent=2)

def load_held_bills():
    try:
        with open(HELD_BILLS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_held_bills(bills):
    with open(HELD_BILLS_FILE, "w") as f:
        json.dump(bills, f, indent=2)

def load_sales():
    try:
        with open(SALES_DATA_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_sales(sd):
    with open(SALES_DATA_FILE, 'w') as f:
        json.dump(sd, f, indent=2)