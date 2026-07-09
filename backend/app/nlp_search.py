import re
from datetime import datetime
from app.db import get_db_connection

def execute_nlp_search(query_str: str) -> list:
    """
    Parses a natural language search, compiles it to a SQL query,
    executes it, and returns the list of matching transactions.
    """
    from app.ai_service import parse_natural_language_search
    
    filters = parse_natural_language_search(query_str)
    
    sql = "SELECT DISTINCT t.id, t.amount, t.merchant, t.payment_mode, t.bank, t.date, t.time, t.sms_source FROM transactions t"
    joins = []
    where_clauses = []
    params = []
    
    # We join with expense_items if filtering by item_name, category, or subcategory
    needs_item_join = False
    if "category" in filters or "item_name" in filters:
        needs_item_join = True
        joins.append("LEFT JOIN expense_items e ON t.id = e.transaction_id")
        
    if "category" in filters:
        where_clauses.append("e.category = ?")
        params.append(filters["category"])
        
    if "merchant" in filters:
        where_clauses.append("t.merchant LIKE ?")
        params.append(f"%{filters['merchant']}%")
        
    if "min_amount" in filters:
        where_clauses.append("t.amount >= ?")
        params.append(filters["min_amount"])
        
    if "max_amount" in filters:
        where_clauses.append("t.amount <= ?")
        params.append(filters["max_amount"])
        
    if "payment_mode" in filters:
        where_clauses.append("t.payment_mode = ?")
        params.append(filters["payment_mode"])
        
    if "item_name" in filters:
        where_clauses.append("(e.item_name LIKE ? OR e.subcategory LIKE ?)")
        params.append(f"%{filters['item_name']}%")
        params.append(f"%{filters['item_name']}%")
        
    if "year" in filters:
        # Date format YYYY-MM-DD
        year_val = str(filters["year"])
        if "month" in filters:
            month_val = str(filters["month"]).zfill(2)
            where_clauses.append("t.date LIKE ?")
            params.append(f"{year_val}-{month_val}-%")
        else:
            where_clauses.append("t.date LIKE ?")
            params.append(f"{year_val}-%")
    elif "month" in filters:
        # If month is specified but no year, search current year's month
        curr_year = datetime.now().year
        month_val = str(filters["month"]).zfill(2)
        where_clauses.append("t.date LIKE ?")
        params.append(f"{curr_year}-{month_val}-%")

    # Construct the final SQL query
    if joins:
        sql += " " + " ".join(joins)
    
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
        
    sql += " ORDER BY t.date DESC, t.time DESC"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "amount": r["amount"],
            "merchant": r["merchant"],
            "payment_mode": r["payment_mode"],
            "bank": r["bank"],
            "date": r["date"],
            "time": r["time"],
            "sms_source": r["sms_source"]
        })
        
    conn.close()
    return results
