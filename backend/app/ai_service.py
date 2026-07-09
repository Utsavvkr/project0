import os
import json
import re
from datetime import datetime
import google.generativeai as genai
from app.db import get_db_connection

# Categories requested by the user
CATEGORIES = [
    "sent money to friend", "sent money to family", "Groceries", "Nutrition", 
    "Medical", "Shopping", "Travel", "Fuel", "Entertainment", "Education", 
    "Rent", "Utilities", "Bills", "Investment", "Personal Care", "Electronics", 
    "Dining", "Coffee", "Subscriptions", "Fitness", "Gifts", "Miscellaneous"
]

def get_api_key():
    # Read from environment or settings database
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key='gemini_api_key'")
            row = cursor.fetchone()
            if row:
                api_key = row["value"]
            conn.close()
        except Exception:
            pass
    return api_key

# --- 1. LOCAL FALLBACK ENGINE ---
def local_categorize_item(item_name: str) -> dict:
    """
    Local fallback classifier based on regex rules.
    Returns: {"category": str, "subcategory": str, "estimated_price": float or None, "quantity": int}
    """
    clean_name = item_name.strip()
    price = None
    qty = 1
    
    # 1. Extract and strip price from the end (e.g. "Rs 100", "100.00", "₹100")
    price_match = re.search(r'(?:Rs\.?|INR|₹)?\s*(\d+(?:\.\d{1,2})?)\s*$', clean_name, re.IGNORECASE)
    if price_match:
        try:
            price = float(price_match.group(1))
            clean_name = clean_name[:price_match.start()].strip()
        except ValueError:
            pass

    # 2. Extract and strip quantity (e.g. "x2", "2x", "2 qty", "2 nos")
    qty_match = re.search(r'\b(?:x|qty|nos|qnty)\s*(\d+)\b|\b(\d+)\s*(?:x|qty|nos|qnty)\b', clean_name, re.IGNORECASE)
    if qty_match:
        try:
            val = qty_match.group(1) or qty_match.group(2)
            qty = int(val)
            clean_name = clean_name.replace(qty_match.group(0), "").strip()
        except ValueError:
            pass
    else:
        # Fallback: check if it starts with a number followed by space (e.g. "2 apples")
        start_qty = re.match(r'^(\d+)\s+([a-zA-Z])', clean_name)
        if start_qty:
            try:
                qty = int(start_qty.group(1))
                clean_name = clean_name[start_qty.end(1):].strip()
            except ValueError:
                pass
            
    # Clean up name from separator characters
    clean_name = re.sub(r'^[-\s\*\•\d]+', '', clean_name).strip() # remove leading dashes/numbers/bullets
    
    name_lower = clean_name.lower()
    
    # Local matching logic
    rules = [
        # sent money to friend
        (r"\b(friend|bro|buddy|guy|roommate|splitwise|pay\s+back|owed)\b", "sent money to friend", "Friend Transfer"),
        # sent money to family
        (r"\b(mom|dad|sister|brother|wife|husband|son|daughter|family|home\s+transfer|rent\s+to\s+parents)\b", "sent money to family", "Family Transfer"),
        # Coffee
        (r"\b(coffee|tea|chai|latte|espresso|cappuccino|starbucks|blue\s+tokai|cafe|ccd)\b", "Coffee", "Coffee Shop"),
        # Nutrition
        (r"\b(chicken|egg|eggs|protein|whey|creatine|fish|meat|beef|pork|mutton|paneer|tofu|tofu|supplements|salad|gym\s+diet)\b", "Nutrition", "Bodybuilding Diet"),
        # Medical
        (r"\b(medicine|tablet|pill|hospital|doctor|clinic|pharmacy|chemist|dentist|paracetamol|vaccine|cough|medical|health)\b", "Medical", "Healthcare"),
        # Shopping (Footwear / Clothing / Retail)
        (r"\b(nike|adidas|puma|shoes|sneakers|footwear|tshirt|shirt|jeans|pants|jacket|dress|clothing|socks|mall|zara|h&m)\b", "Shopping", "Clothing & Apparel"),
        (r"\b(shopping|amazon|flipkart|myntra|meesho|order|purchase)\b", "Shopping", "Online Retail"),
        # Fuel
        (r"\b(petrol|diesel|fuel|cng|gasoline|shell|hp\s+petrol|bpcl|iocl)\b", "Fuel", "Vehicle Fuel"),
        # Travel
        (r"\b(uber|ola|rapido|cab|taxi|metro|bus|train|flight|ticket|travel|auto|rickshaw|irctc|airasia|indigo)\b", "Travel", "Commute"),
        # Entertainment
        (r"\b(movie|cinema|netflix|spotify|disney|hotstar|youtube\s+premium|concert|game|ps5|xbox|steam|playstation|arcade|pub|bar|club|party)\b", "Entertainment", "Leisure"),
        # Education
        (r"\b(book|books|course|udemy|coursera|tuition|school|college|fees|stationery|pen|pencil|exam)\b", "Education", "Learning"),
        # Rent
        (r"\b(rent|maintenance|flat\s+rent|pg\s+rent|deposit)\b", "Rent", "Housing"),
        # Utilities
        (r"\b(electricity|water|wifi|internet|broadband|gas\s+cylinder|piped\s+gas|trash|utility)\b", "Utilities", "Utilities"),
        # Bills
        (r"\b(recharge|jio|airtel|vi|mobile\s+bill|postpaid|prepaid|dth|cable|credit\s+card\s+payment|insurance\s+premium|tax)\b", "Bills", "Regular Bills"),
        # Investment
        (r"\b(mutual\s+fund|stock|shares|sip|investment|gold|crypto|bitcoin|eth|groww|zerodha|fixed\s+deposit)\b", "Investment", "Savings & Stocks"),
        # Personal Care
        (r"\b(shampoo|soap|toothpaste|brush|facewash|salon|barber|haircut|parlour|makeup|perfume|deodorant|waxing|trimmer)\b", "Personal Care", "Grooming"),
        # Electronics
        (r"\b(laptop|mobile|phone|iphone|macbook|charger|mouse|keyboard|monitor|headphones|earbuds|tv|electronics|gadget|usb|router)\b", "Electronics", "Gadgets"),
        # Dining
        (r"\b(restaurant|zomato|swiggy|dining|lunch|dinner|breakfast|pizza|burger|subway|kfc|mcdonald|food\s+court|food|eatout)\b", "Dining", "Restaurants"),
        # Fitness
        (r"\b(gym|fitness|yoga|workout|crossfit|cult|cultfit|dumbbell|sports|badminton|football|cricket|running)\b", "Fitness", "Gym Membership"),
        # Gifts
        (r"\b(gift|birthday|anniversary|flowers|bouquet|chocolate|rakhi|diwali\s+gift)\b", "Gifts", "Present"),
        # Groceries (general kitchen items)
        (r"\b(milk|bread|groceries|grocery|dmart|bigbasket|blinkit|zepto|sugar|rice|wheat|atta|oil|butter|cheese|vegetables|veg|fruits|apple|banana|onion|potato|salt|spices|shampoo|soap)\b", "Groceries", "Groceries")
    ]
    
    matched_cat = "Miscellaneous"
    matched_sub = "General"
    
    for regex, cat, sub in rules:
        if re.search(regex, name_lower):
            matched_cat = cat
            matched_sub = sub
            break
            
    # Clean item name to be neat
    if not clean_name:
        clean_name = "Item"
        
    return {
        "item_name": clean_name.title(),
        "category": matched_cat,
        "subcategory": matched_sub,
        "estimated_price": price,
        "quantity": qty
    }

# --- 2. AI CATEGORIZATION (GEMINI) ---
def ai_categorize_items(items_text: str) -> dict:
    """
    Uses Gemini API to categorize list of items, splitting into categories/subcategories.
    Falls back to local_categorize_item if API fails or API key is missing.
    """
    # Split items by newline or comma
    raw_items = [i.strip() for i in re.split(r'\n|,', items_text) if i.strip()]
    if not raw_items:
        return {"category": "Miscellaneous", "items": []}
        
    api_key = get_api_key()
    if not api_key:
        # Run local fallback
        parsed_items = [local_categorize_item(item) for item in raw_items]
        # Find dominant category
        categories_tally = {}
        for item in parsed_items:
            categories_tally[item["category"]] = categories_tally.get(item["category"], 0) + 1
        dominant_category = max(categories_tally, key=categories_tally.get) if categories_tally else "Miscellaneous"
        return {
            "category": dominant_category,
            "items": parsed_items
        }

    # Gemini API prompt
    prompt = f"""
    You are an expert personal finance AI. You will be given a list of items bought in a transaction.
    Analyze the list and categorize each item into one of the following official categories:
    {', '.join(CATEGORIES)}.
    
    For each item, output:
    1. Cleaned item name (proper casing, removing quantities/prices from the name string).
    2. The selected official category.
    3. An intelligent subcategory (e.g. for Nike Shoes under Shopping, subcategory is Footwear. For Eggs under Nutrition, subcategory is Eggs/Poultry).
    4. Estimated price (if mentioned in the item string, otherwise null).
    5. Quantity (if mentioned, otherwise 1).
    
    Input items list:
    \"\"\"{items_text}\"\"\"
    
    Return JSON only in the following schema:
    {{
      "category": "dominant_category_name_for_entire_transaction",
      "items": [
        {{
          "item_name": "Item Name",
          "category": "Official Category Name",
          "subcategory": "Subcategory Name",
          "estimated_price": 120.00, // or null
          "quantity": 1 // integer
        }}
      ]
    }}
    Do not add markdown formatting or backticks. Return raw JSON string.
    """
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean json markers if LLM returns markdown codeblocks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        # Fail gracefully to local fallback
        print(f"Gemini API categorization error: {e}. Falling back to local rules.")
        parsed_items = [local_categorize_item(item) for item in raw_items]
        categories_tally = {}
        for item in parsed_items:
            categories_tally[item["category"]] = categories_tally.get(item["category"], 0) + 1
        dominant_category = max(categories_tally, key=categories_tally.get) if categories_tally else "Miscellaneous"
        return {
            "category": dominant_category,
            "items": parsed_items
        }

# --- 3. NATURAL LANGUAGE SEARCH PARSER ---
def parse_natural_language_search(query: str) -> dict:
    """
    Compiles a natural language search query into structural filters.
    Example: "grocery expenses in June" -> {"category": "Groceries", "month": 6}
    """
    api_key = get_api_key()
    if not api_key:
        return local_nlp_search(query)
        
    prompt = f"""
    You are an AI search assistant for an expense tracker. Convert the following natural language query into database filters.
    Official categories: {', '.join(CATEGORIES)}.
    Current year is {datetime.now().year}.
    
    Search query: "{query}"
    
    Output JSON only in this schema:
    {{
      "category": "CategoryName", // string, optional, must match official list
      "merchant": "MerchantName", // string, optional
      "min_amount": 500.0, // float, optional
      "max_amount": 1000.0, // float, optional
      "year": 2026, // int, optional
      "month": 6, // int, optional (1-12)
      "item_name": "item", // string, optional
      "payment_mode": "UPI" // UPI, Card, Cash, Wallet, Bank Transfer, Other, optional
    }}
    Return only raw JSON. Do not add markdown formatting or backticks.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini API NLP search error: {e}. Falling back to local parser.")
        return local_nlp_search(query)

def local_nlp_search(query: str) -> dict:
    """
    Rule-based local natural language search compiler.
    """
    filters = {}
    query_lower = query.lower()
    
    # 1. Match category
    stem_mappings = {
        "grocery": "Groceries",
        "groceries": "Groceries",
        "friend": "sent money to friend",
        "friends": "sent money to friend",
        "family": "sent money to family",
        "families": "sent money to family",
        "medical": "Medical",
        "medicine": "Medical",
        "shop": "Shopping",
        "shopping": "Shopping",
        "travel": "Travel",
        "fuel": "Fuel",
        "entertainment": "Entertainment",
        "education": "Education",
        "rent": "Rent",
        "utilities": "Utilities",
        "utility": "Utilities",
        "bills": "Bills",
        "bill": "Bills",
        "investment": "Investment",
        "personal": "Personal Care",
        "electronics": "Electronics",
        "electronic": "Electronics",
        "dining": "Dining",
        "dine": "Dining",
        "coffee": "Coffee",
        "subscriptions": "Subscriptions",
        "subscription": "Subscriptions",
        "fitness": "Fitness",
        "gifts": "Gifts",
        "gift": "Gifts",
        "miscellaneous": "Miscellaneous",
        "misc": "Miscellaneous"
    }
    
    matched_cat = None
    for stem, official_cat in stem_mappings.items():
        if stem in query_lower:
            matched_cat = official_cat
            break
            
    if not matched_cat:
        for cat in CATEGORIES:
            if cat.lower() in query_lower:
                matched_cat = cat
                break
                
    if matched_cat:
        filters["category"] = matched_cat
            
    # 2. Match amount operators (above, below, greater, less)
    amt_above = re.search(r'(?:above|greater than|more than|>=|>)\s*(?:Rs\.?|₹|INR)?\s*(\d+)', query_lower)
    if amt_above:
        filters["min_amount"] = float(amt_above.group(1))
        
    amt_below = re.search(r'(?:below|less than|under|<=|<)\s*(?:Rs\.?|₹|INR)?\s*(\d+)', query_lower)
    if amt_below:
        filters["max_amount"] = float(amt_below.group(1))
        
    # Exact amount search if no operator
    if "min_amount" not in filters and "max_amount" not in filters:
        exact_amt = re.search(r'\b(?:Rs\.?|₹|INR)?\s*(\d+)\b', query_lower)
        if exact_amt:
            # Avoid matching year like 2026
            val = int(exact_amt.group(1))
            if val not in [2024, 2025, 2026, 2027]:
                filters["min_amount"] = float(val)
                filters["max_amount"] = float(val)

    # 3. Match Months
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, 
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, 
        "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10, 
        "november": 11, "nov": 11, "december": 12, "dec": 12
    }
    for m_name, m_num in months.items():
        if re.search(rf"\b{m_name}\b", query_lower):
            filters["month"] = m_num
            break
            
    # 4. Match Year
    year_match = re.search(r'\b(20\d{2})\b', query_lower)
    if year_match:
        filters["year"] = int(year_match.group(1))
    else:
        # If month is specified but no year, default to current year
        if "month" in filters:
            filters["year"] = datetime.now().year

    # 5. Match Merchant
    merchants = ["amazon", "flipkart", "swiggy", "zomato", "dmart", "netflix", "spotify", "uber", "ola", "starbucks", "reliance"]
    for m in merchants:
        if m in query_lower:
            filters["merchant"] = m.upper()
            break
            
    # 6. Match Payment mode
    if "upi" in query_lower:
        filters["payment_mode"] = "UPI"
    elif "card" in query_lower:
        filters["payment_mode"] = "Card"
    elif "cash" in query_lower:
        filters["payment_mode"] = "Cash"
    elif "wallet" in query_lower:
        filters["payment_mode"] = "Wallet"

    # 7. Check generic items if nothing else matches
    # e.g., "how much did I spend on tea?" -> item_name = "tea"
    item_match = re.search(r'(?:spent on|buy|for)\s+([A-Za-z0-9]+)', query_lower)
    if item_match:
        val = item_match.group(1).strip()
        if val not in [cat.lower() for cat in CATEGORIES] and val not in months:
            filters["item_name"] = val

    return filters

# --- 4. AI INSIGHTS GENERATOR ---
def generate_spending_insights(insights_data: list) -> list:
    """
    Generates intelligent text insights based on recent transactions.
    Falls back to simple math rules if API fails.
    """
    api_key = get_api_key()
    if not api_key:
        return local_insights(insights_data)
        
    prompt = f"""
    You are a personal financial advisor AI. Analyze the following budget and spending statistics for the user and return exactly 4 bullet-point insights/observations.
    Provide constructive feedback, point out significant changes (percentage increases/decreases), and suggest money-saving tips based on these numbers.
    
    Data:
    {json.dumps(insights_data, indent=2)}
    
    Return a JSON array of strings, like this:
    [
      "You spent 24% more on groceries than last month. Consider shopping at DMart for bulk discounts.",
      "Dining expenses increased by ₹3,200. You visited Swiggy 5 times this week.",
      "Coffee purchases reduced by 40%. Great job cutting down on Starbucks!",
      "You have reached 95% of your Shopping budget. Consider pausing new purchases."
    ]
    Do not add markdown formatting or backticks. Return raw JSON.
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini API insights error: {e}. Falling back to local engine.")
        return local_insights(insights_data)

def local_insights(insights_data: list) -> list:
    """
    Rule-based generator for user insights.
    """
    insights = []
    # insights_data is a list of dicts with category, limit, spent, last_month_spent, etc.
    # Let's write simple rules
    for item in insights_data:
        cat = item.get("category")
        spent = item.get("spent", 0)
        limit = item.get("limit", 0)
        last_spent = item.get("last_month_spent", 0)
        
        # Budget utilization alerts
        if limit > 0:
            pct = (spent / limit) * 100
            if pct >= 100:
                insights.append(f"⚠️ You've exceeded your {cat} budget of ₹{limit:.0f} (Spent: ₹{spent:.0f}). Consider freezing further spending in this category.")
            elif pct >= 90:
                insights.append(f"⚠️ Warning: You have utilized {pct:.0f}% of your {cat} budget (Limit: ₹{limit:.0f}). Only ₹{(limit - spent):.0f} left.")
            elif pct >= 75:
                insights.append(f"ℹ️ You spent {pct:.0f}% of your {cat} budget. You are on track but watch out for additional expenditures.")

        # Comparison alerts
        if last_spent > 0 and spent > 0:
            change = ((spent - last_spent) / last_spent) * 100
            if change > 20:
                insights.append(f"📈 Your {cat} expenses are up by {change:.0f}% compared to last month (₹{spent:.0f} vs ₹{last_spent:.0f}).")
            elif change < -20:
                insights.append(f"📉 Great job! Your {cat} expenses decreased by {abs(change):.0f}% compared to last month.")

    # Fill up with generic helpful suggestions if short
    if len(insights) < 2:
        insights.append("💡 Tip: Try saving more by moving credit card payments to UPI to avoid overspending impulses.")
    if len(insights) < 3:
        insights.append("💡 Dining expenses represent a substantial chunk of miscellaneous spending. Try cooking at home on weekends.")
    if len(insights) < 4:
        insights.append("💡 Good job keeping your Fuel and Travel spending consistent this month.")
        
    return insights[:4]
