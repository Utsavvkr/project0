import re
from datetime import datetime

def parse_sms(sms_text: str, sender: str = "") -> dict:
    """
    Parses typical Indian bank SMS alerts to extract transaction details.
    Examples of handled SMS patterns:
    - "Rs. 850 debited via UPI to DMART"
    - "Rs. 1,200.00 spent on HDFC Card ending 1234 at AMAZON on 09-07-2026."
    - "Amt debited Rs. 500.00 from A/C XX3210 on 09-Jul-26 19:22:00 to VPA zomato@paytm (UPI Ref 678912)"
    - "Your HDFC A/C xx4321 has been debited with INR 250.00 via NetBanking on 09-07-26."
    """
    amount = 0.0
    merchant = "Unknown Merchant"
    payment_mode = "UPI"
    bank = "Unknown Bank"
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    txn_id = ""

    # Clean the SMS text for uniform spacing
    cleaned_text = " ".join(sms_text.split())

    # --- 1. Detect Bank ---
    bank_patterns = {
        r"SBI|STATE BANK": "SBI",
        r"HDFC": "HDFC Bank",
        r"ICICI": "ICICI Bank",
        r"AXIS": "Axis Bank",
        r"KOTAK": "Kotak Bank",
        r"PNB|PUNJAB NATIONAL": "PNB",
        r"BOB|BANK OF BARODA": "BOB",
        r"PAYTM": "Paytm Bank",
        r"PHONEPE": "PhonePe",
        r"GPAY": "Google Pay"
    }
    
    # Check sender first (e.g. AD-HDFCBK -> HDFC Bank)
    sender_upper = sender.upper() if sender else ""
    for pattern, bank_name in bank_patterns.items():
        if re.search(pattern, sender_upper):
            bank = bank_name
            break
            
    # If not found in sender, check body
    if bank == "Unknown Bank":
        for pattern, bank_name in bank_patterns.items():
            if re.search(pattern, cleaned_text, re.IGNORECASE):
                bank = bank_name
                break

    # --- 2. Extract Amount ---
    # Matches: Rs. 850, Rs.850.00, Rs 1,200.00, INR 500, Rs. 1,200, etc.
    amt_match = re.search(
        r"(?:Rs\.?|INR|Amt\.?|debited with|spent|value of)\s*([0-9,]+(?:\.[0-9]{2})?)",
        cleaned_text,
        re.IGNORECASE
    )
    if amt_match:
        val_str = amt_match.group(1).replace(",", "")
        try:
            amount = float(val_str)
        except ValueError:
            pass
    else:
        # Fallback amount regex
        alt_amt_match = re.search(r"([0-9,]+\.[0-9]{2})", cleaned_text)
        if alt_amt_match:
            try:
                amount = float(alt_amt_match.group(1).replace(",", ""))
            except ValueError:
                pass

    # --- 3. Extract Merchant ---
    # Find words following "to ", "at ", "vpa ", "info: " or "spent on "
    merchant_patterns = [
        r"to\s+([A-Za-z0-9\s\.\*#&]+?)(?:\s+Ref|\s+on|\s+via|\s+from|\s+ending|\s+\.|\Z)",
        r"at\s+([A-Za-z0-9\s\.\*#&]+?)(?:\s+on|\s+via|\s+using|\s+Ref|\s+\.|\Z)",
        r"VPA\s+([a-zA-Z0-9\.\-_@]+)",
        r"info:\s*([A-Za-z0-9\s\.\*#&]+?)(?:\s+on|\s+via|\s+Ref|\s+\.|\Z)"
    ]
    for pattern in merchant_patterns:
        m_match = re.search(pattern, cleaned_text, re.IGNORECASE)
        if m_match:
            merchant = m_match.group(1).strip()
            # Clean up merchant (if it's a UPI handle like zomato@paytm, clean to ZOMATO)
            if "@" in merchant:
                merchant = merchant.split("@")[0]
            # Replace multiple spaces
            merchant = " ".join(merchant.split())
            break

    if merchant == "Unknown Merchant" or not merchant:
        # If no merchant matches, look for commonly known merchant names in text
        known_merchants = ["DMART", "AMAZON", "FLIPKART", "SWIGGY", "ZOMATO", "UBER", "OLA", "NETFLIX", "SPOTIFY", "STARBUCKS", "PETROL", "SHELL", "RELIANCE"]
        for km in known_merchants:
            if km.lower() in cleaned_text.lower():
                merchant = km
                break

    # --- 4. Detect Payment Mode ---
    if re.search(r"UPI|VPA|BHIM", cleaned_text, re.IGNORECASE):
        payment_mode = "UPI"
    elif re.search(r"Credit Card|credit|cc", cleaned_text, re.IGNORECASE):
        payment_mode = "Card"
    elif re.search(r"Debit Card|debit|dc|card ending", cleaned_text, re.IGNORECASE):
        payment_mode = "Card"
    elif re.search(r"NetBanking|Net Banking|Transfer|NEFT|RTGS|IMPS", cleaned_text, re.IGNORECASE):
        payment_mode = "Bank Transfer"
    elif re.search(r"Wallet|Paytm|PhonePe Wallet", cleaned_text, re.IGNORECASE):
        payment_mode = "Wallet"
    elif re.search(r"Cash", cleaned_text, re.IGNORECASE):
        payment_mode = "Cash"
    else:
        payment_mode = "UPI"  # Default in modern Indian context

    # --- 5. Extract Transaction ID ---
    txn_patterns = [
        r"(?:UPI Ref|Ref No|Ref|Txn ID|Txn|Reference)\s*[:\-#]?\s*([A-Za-z0-9]+)",
        r"(?:UPI\s+Ref\s+No\s+)([0-9]+)"
    ]
    for pattern in txn_patterns:
        t_match = re.search(pattern, cleaned_text, re.IGNORECASE)
        if t_match:
            txn_id = t_match.group(1).strip()
            break

    # --- 6. Extract Date and Time ---
    # Dates: 09-07-2026, 09/07/26, 09-Jul-26, 09Jul26
    date_match = re.search(
        r"(\d{1,2}[-/\s]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[-/\s]?\d{2,4}|\d{2}[-/\s]\d{2}[-/\s]\d{2,4})",
        cleaned_text,
        re.IGNORECASE
    )
    if date_match:
        raw_date = date_match.group(1)
        # Try to parse it
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y", "%d-%b-%y", "%d-%b-%Y", "%d%b%y"):
            try:
                dt = datetime.strptime(raw_date.replace(" ", ""), fmt)
                date_str = dt.strftime("%Y-%m-%d")
                break
            except ValueError:
                pass
                
    time_match = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", cleaned_text)
    if time_match:
        time_str = time_match.group(1)
        # Format HH:MM
        parts = time_str.split(":")
        time_str = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"

    return {
        "amount": amount,
        "merchant": merchant.upper(),
        "payment_mode": payment_mode,
        "bank": bank,
        "date": date_str,
        "time": time_str,
        "transaction_id": txn_id,
        "sms_source": sender if sender else "SMS"
    }

if __name__ == "__main__":
    # Test cases
    test_sms = [
        "Rs. 850 debited via UPI to DMART",
        "Rs 500.00 debited from A/C ...1234 on 09-07-26 to VPA dmart@okaxis (Ref No 1234567890)",
        "Txn of Rs. 150.00 on Credit Card XX7890 at STARBUCKS on 09/07/26 14:30. Limit Avbl: Rs. 45000",
        "Alert: Rs.450.00 debited from SBI Account ...4321 via UPI to SWIGGY Ref 12345",
    ]
    for s in test_sms:
        print(f"SMS: {s}")
        print(f"Parsed: {parse_sms(s)}\n")
