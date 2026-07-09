import os
import sys
import csv
import io
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Add the directory containing main.py to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, get_db_connection
from app.sms_parser import parse_sms
from app.ai_service import ai_categorize_items
from app.nlp_search import execute_nlp_search
from app.insights import get_insights_and_stats

app = FastAPI(title="ExpenseIQ Backend Server", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup DB initialization
@app.on_event("startup")
def startup_event():
    init_db()

# Pydantic Schemas
class SMSParseRequest(BaseModel):
    sms_text: str
    sender: Optional[str] = ""

class CategorizeRequest(BaseModel):
    items_text: str

class ExpenseItemModel(BaseModel):
    item_name: str
    category: str
    subcategory: Optional[str] = "General"
    estimated_price: Optional[float] = None
    quantity: Optional[int] = 1
    notes: Optional[str] = ""

class TransactionCreateRequest(BaseModel):
    amount: float
    merchant: str
    payment_mode: str
    bank: str
    date: str
    time: str
    sms_source: Optional[str] = "Manual"
    items: Optional[List[ExpenseItemModel]] = []

class BudgetUpdateRequest(BaseModel):
    category: str
    amount_limit: float

class SettingsUpdateRequest(BaseModel):
    key: str
    value: str

# Helper to update cached budget spent amount
def recalculate_budgets():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Reset all spent amounts
    cursor.execute("UPDATE budgets SET spent_amount = 0")
    
    # Sum up this month's items
    now = datetime.now()
    this_month_start = f"{now.year}-{str(now.month).zfill(2)}-01"
    this_month_end = f"{now.year}-{str(now.month).zfill(2)}-31" # SQLite handles boundary well
    
    cursor.execute("""
        SELECT e.category, SUM(e.estimated_price * e.quantity) as spent
        FROM expense_items e
        JOIN transactions t ON e.transaction_id = t.id
        WHERE t.date BETWEEN ? AND ?
        GROUP BY e.category
    """, (this_month_start, this_month_end))
    
    rows = cursor.fetchall()
    for row in rows:
        cursor.execute("""
            UPDATE budgets SET spent_amount = ? WHERE category = ?
        """, (row["spent"] or 0.0, row["category"]))
        
    conn.commit()
    conn.close()

# --- API ENDPOINTS ---

@app.post("/api/sms/parse")
def api_parse_sms(payload: SMSParseRequest):
    try:
        details = parse_sms(payload.sms_text, payload.sender)
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/categorize")
def api_categorize(payload: CategorizeRequest):
    try:
        result = ai_categorize_items(payload.items_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def api_get_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC, time DESC")
    transactions = [dict(row) for row in cursor.fetchall()]
    
    # Fetch items for each transaction
    for tx in transactions:
        cursor.execute("SELECT * FROM expense_items WHERE transaction_id = ?", (tx["id"],))
        tx["items"] = [dict(row) for row in cursor.fetchall()]
        
    conn.close()
    return transactions

@app.post("/api/transactions")
def api_create_transaction(payload: TransactionCreateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Insert transaction
        cursor.execute("""
            INSERT INTO transactions (amount, merchant, payment_mode, bank, date, time, sms_source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.amount,
            payload.merchant.upper(),
            payload.payment_mode,
            payload.bank,
            payload.date,
            payload.time,
            payload.sms_source,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        txn_id = cursor.lastrowid
        
        # 2. Insert items
        for item in payload.items:
            # If price is none, we distribute transaction amount amongst items (simplified fallback)
            item_price = item.estimated_price
            if item_price is None:
                item_price = payload.amount / max(len(payload.items), 1)
                
            cursor.execute("""
                INSERT INTO expense_items (transaction_id, item_name, category, subcategory, estimated_price, quantity, source, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                txn_id,
                item.item_name.title(),
                item.category,
                item.subcategory,
                item_price,
                item.quantity,
                "SMS" if payload.sms_source != "Manual" else "Manual",
                item.notes
            ))
            
        conn.commit()
        conn.close()
        
        # Recalculate budget spent
        recalculate_budgets()
        
        return {"status": "success", "transaction_id": txn_id}
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/transactions/{txn_id}")
def api_delete_transaction(txn_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        cursor.execute("DELETE FROM expense_items WHERE transaction_id = ?", (txn_id,))
        conn.commit()
        conn.close()
        recalculate_budgets()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/budgets")
def api_get_budgets():
    # Force recalculation to ensure sync
    recalculate_budgets()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM budgets")
    budgets = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return budgets

@app.post("/api/budgets")
def api_update_budget(payload: BudgetUpdateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO budgets (category, amount_limit, spent_amount)
            VALUES (?, ?, 0)
            ON CONFLICT(category) DO UPDATE SET amount_limit = excluded.amount_limit
        """, (payload.category, payload.amount_limit))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
def api_search_expenses(q: str = Query(..., min_length=1)):
    try:
        results = execute_nlp_search(q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/insights")
def api_get_insights():
    try:
        return get_insights_and_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports")
def api_get_reports(period: str = "monthly"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    this_month_start = f"{now.year}-{str(now.month).zfill(2)}-01"
    
    # 1. Category Chart
    cursor.execute("""
        SELECT e.category, SUM(e.estimated_price * e.quantity) as spent
        FROM expense_items e
        JOIN transactions t ON e.transaction_id = t.id
        WHERE t.date >= ?
        GROUP BY e.category
    """, (this_month_start,))
    category_data = [dict(row) for row in cursor.fetchall()]
    
    # 2. Payment Method Chart
    cursor.execute("""
        SELECT payment_mode, SUM(amount) as spent
        FROM transactions
        WHERE date >= ?
        GROUP BY payment_mode
    """, (this_month_start,))
    payment_data = [dict(row) for row in cursor.fetchall()]
    
    # 3. Monthly Trend Line Chart (Last 6 Months)
    cursor.execute("""
        SELECT strftime('%Y-%m', date) as month, SUM(amount) as spent
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
        LIMIT 6
    """)
    trend_data = [dict(row) for row in cursor.fetchall()]
    trend_data.reverse() # Chronological
    
    conn.close()
    
    return {
        "category_shares": category_data,
        "payment_shares": payment_data,
        "monthly_trend": trend_data
    }

@app.get("/api/settings")
def api_get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return settings

@app.post("/api/settings")
def api_update_settings(payload: SettingsUpdateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (payload.key, payload.value))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
def api_export_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, amount, merchant, payment_mode, bank, date, time, sms_source FROM transactions")
    tx_rows = cursor.fetchall()
    
    # Write to a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Transaction ID", "Amount", "Merchant", "Payment Mode", "Bank", "Date", "Time", "SMS Source"])
    for r in tx_rows:
        writer.writerow([r["id"], r["amount"], r["merchant"], r["payment_mode"], r["bank"], r["date"], r["time"], r["sms_source"]])
        
    conn.close()
    
    response = StreamingResponse(io.BytesIO(output.getvalue().encode("utf-8")), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=expenseiq_transactions.csv"
    return response

# Serve Web Simulator files
@app.get("/")
def serve_index():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
    )

# Mount Static Folder
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
