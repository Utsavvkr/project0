from datetime import datetime, timedelta
import calendar
from app.db import get_db_connection
from app.ai_service import generate_spending_insights

def get_month_date_range(year: int, month: int):
    """Returns the start and end dates for a month in YYYY-MM-DD format."""
    num_days = calendar.monthrange(year, month)[1]
    start_date = f"{year}-{str(month).zfill(2)}-01"
    end_date = f"{year}-{str(month).zfill(2)}-{str(num_days).zfill(2)}"
    return start_date, end_date

def get_insights_and_stats() -> dict:
    """
    Computes all database statistics and calls AI to generate insights.
    """
    now = datetime.now()
    this_year, this_month = now.year, now.month
    
    # Calculate last month
    if this_month == 1:
        last_year, last_month = this_year - 1, 12
    else:
        last_year, last_month = this_year, this_month - 1
        
    this_month_start, this_month_end = get_month_date_range(this_year, this_month)
    last_month_start, last_month_end = get_month_date_range(last_year, last_month)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch budgets and spent totals
    # This month category spent
    cursor.execute("""
        SELECT e.category, SUM(e.estimated_price * e.quantity) as spent
        FROM expense_items e
        JOIN transactions t ON e.transaction_id = t.id
        WHERE t.date BETWEEN ? AND ?
        GROUP BY e.category
    """, (this_month_start, this_month_end))
    this_month_spent = {row["category"]: row["spent"] or 0.0 for row in cursor.fetchall()}
    
    # Last month category spent
    cursor.execute("""
        SELECT e.category, SUM(e.estimated_price * e.quantity) as spent
        FROM expense_items e
        JOIN transactions t ON e.transaction_id = t.id
        WHERE t.date BETWEEN ? AND ?
        GROUP BY e.category
    """, (last_month_start, last_month_end))
    last_month_spent = {row["category"]: row["spent"] or 0.0 for row in cursor.fetchall()}
    
    # Fetch budget limits
    cursor.execute("SELECT category, amount_limit FROM budgets")
    budgets = {row["category"]: row["amount_limit"] for row in cursor.fetchall()}
    
    # Collate data for AI engine
    insights_input = []
    all_categories = set(list(this_month_spent.keys()) + list(last_month_spent.keys()) + list(budgets.keys()))
    
    for cat in all_categories:
        insights_input.append({
            "category": cat,
            "limit": budgets.get(cat, 0.0),
            "spent": this_month_spent.get(cat, 0.0),
            "last_month_spent": last_month_spent.get(cat, 0.0)
        })
        
    # Generate AI/Fallback text insights
    text_insights = generate_spending_insights(insights_input)
    
    # 2. General Stats
    # Total spent this month
    cursor.execute("""
        SELECT SUM(amount) as total FROM transactions 
        WHERE date BETWEEN ? AND ?
    """, (this_month_start, this_month_end))
    month_total = cursor.fetchone()["total"] or 0.0
    
    # Total spent last month
    cursor.execute("""
        SELECT SUM(amount) as total FROM transactions 
        WHERE date BETWEEN ? AND ?
    """, (last_month_start, last_month_end))
    last_month_total = cursor.fetchone()["total"] or 0.0
    
    # Today's spent
    today_str = now.strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) as total FROM transactions WHERE date = ?", (today_str,))
    today_total = cursor.fetchone()["total"] or 0.0
    
    # Current week's spent (last 7 days)
    week_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(amount) as total FROM transactions WHERE date BETWEEN ? AND ?", (week_ago_str, today_str))
    week_total = cursor.fetchone()["total"] or 0.0
    
    # Total transactions
    cursor.execute("SELECT COUNT(*) as count FROM transactions")
    total_txns = cursor.fetchone()["count"] or 0
    
    # Top Category
    cursor.execute("""
        SELECT e.category, SUM(e.estimated_price * e.quantity) as total_spent
        FROM expense_items e
        JOIN transactions t ON e.transaction_id = t.id
        GROUP BY e.category
        ORDER BY total_spent DESC
        LIMIT 1
    """)
    top_cat_row = cursor.fetchone()
    top_category = top_cat_row["category"] if top_cat_row else "None"
    
    # Top Merchant
    cursor.execute("""
        SELECT merchant, SUM(amount) as total_spent
        FROM transactions
        GROUP BY merchant
        ORDER BY total_spent DESC
        LIMIT 1
    """)
    top_merch_row = cursor.fetchone()
    top_merchant = top_merch_row["merchant"] if top_merch_row else "None"
    
    # Most Purchased Item
    cursor.execute("""
        SELECT item_name, COUNT(*) as count
        FROM expense_items
        GROUP BY item_name
        ORDER BY count DESC, id DESC
        LIMIT 1
    """)
    most_purchased_row = cursor.fetchone()
    most_purchased = most_purchased_row["item_name"] if most_purchased_row else "None"
    
    # Most Expensive Item
    cursor.execute("""
        SELECT item_name, MAX(estimated_price) as price
        FROM expense_items
        LIMIT 1
    """)
    most_expensive_row = cursor.fetchone()
    most_expensive = most_expensive_row["item_name"] if most_expensive_row and most_expensive_row["item_name"] else "None"
    
    # Average spends
    # Get number of unique active days in database
    cursor.execute("SELECT COUNT(DISTINCT date) as days FROM transactions")
    active_days = cursor.fetchone()["days"] or 1
    avg_daily_spend = month_total / 30.0 # Standard month average
    avg_weekly_spend = avg_daily_spend * 7.0
    avg_monthly_spend = month_total # Simple approximation
    
    # Highest Spending Day
    cursor.execute("""
        SELECT date, SUM(amount) as total_spent
        FROM transactions
        GROUP BY date
        ORDER BY total_spent DESC
        LIMIT 1
    """)
    highest_day_row = cursor.fetchone()
    highest_day = highest_day_row["date"] if highest_day_row else "None"
    
    # Highest Spending Month
    cursor.execute("""
        SELECT strftime('%Y-%m', date) as mth, SUM(amount) as total_spent
        FROM transactions
        GROUP BY mth
        ORDER BY total_spent DESC
        LIMIT 1
    """)
    highest_month_row = cursor.fetchone()
    highest_month = highest_month_row["mth"] if highest_month_row else "None"
    
    conn.close()
    
    return {
        "dashboard_stats": {
            "month_spending": month_total,
            "week_spending": week_total,
            "today_spending": today_total,
            "total_transactions": total_txns,
            "top_category": top_category,
            "top_merchant": top_merchant,
            "last_month_spending": last_month_total
        },
        "statistics": {
            "most_purchased_item": most_purchased,
            "most_expensive_item": most_expensive,
            "avg_daily_spend": avg_daily_spend,
            "avg_weekly_spend": avg_weekly_spend,
            "avg_monthly_spend": avg_monthly_spend,
            "highest_spending_day": highest_day,
            "highest_spending_month": highest_month,
            "most_visited_merchant": top_merchant,
            "monthly_savings_estimate": max(50000.0 - month_total, 0.0) # Mock income = 50,000
        },
        "insights": text_insights
    }
