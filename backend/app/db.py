import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "expense_iq.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            merchant TEXT,
            payment_mode TEXT,
            bank TEXT,
            date TEXT, -- YYYY-MM-DD
            time TEXT, -- HH:MM:SS
            sms_source TEXT,
            created_at TEXT
        )
    """)
    
    # 2. Expense Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            estimated_price REAL,
            quantity INTEGER DEFAULT 1,
            source TEXT, -- 'SMS', 'Manual', 'OCR'
            notes TEXT,
            FOREIGN KEY(transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
        )
    """)
    
    # 3. Budgets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            category TEXT PRIMARY KEY,
            amount_limit REAL NOT NULL,
            spent_amount REAL DEFAULT 0
        )
    """)
    
    # 4. Settings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    # Seed default settings
    default_settings = [
        ("currency", "₹"),
        ("language", "English"),
        ("theme", "Dark"),
        ("gemini_api_key", ""),
        ("ocr_mock_enabled", "true")
    ]
    for key, val in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
        
    # Seed default budgets
    default_budgets = [
        ("Groceries", 8000.0),
        ("Nutrition", 5000.0),
        ("Medical", 3000.0),
        ("Shopping", 10000.0),
        ("Travel", 4000.0),
        ("Fuel", 6000.0),
        ("Entertainment", 5000.0),
        ("Dining", 4000.0),
        ("Coffee", 1500.0),
        ("Electronics", 15000.0),
        ("Miscellaneous", 3000.0)
    ]
    for category, limit in default_budgets:
        cursor.execute("INSERT OR IGNORE INTO budgets (category, amount_limit, spent_amount) VALUES (?, ?, 0)", (category, limit))
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
