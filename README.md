# ExpenseIQ – AI Powered Personal Expense Tracker

ExpenseIQ is a premium, AI-powered expense tracking application that automatically intercepts transaction notifications from SMS, parses amounts, merchants, banks, and payment modes, alerts the user to describe what they purchased, and utilizes AI to split and categorize the purchase items into structural category/subcategory records.

---

## 📁 Repository Structure

```
project0/
├── backend/
│   ├── app/
│   │   ├── ai_service.py       # Gemini API SDK integration & offline fallback categorizer
│   │   ├── db.py               # SQLite schema and initialization script
│   │   ├── insights.py         # Monthly comparison, metrics, and suggestions engine
│   │   ├── nlp_search.py       # Compiles natural query text to SQLite queries
│   │   └── sms_parser.py       # Regex parser optimized for Indian bank alerts
│   ├── static/
│   │   └── index.html          # High-fidelity Android device Web Simulator
│   ├── main.py                 # FastAPI endpoints and static content mount
│   ├── requirements.txt        # Backend dependencies list
│   └── test_parser.py          # Python unit tests for parsers and matchers
│
└── flutter_app/
    ├── lib/
    │   ├── models.dart         # Dart data models mapping to database
    │   ├── services/
    │   │   ├── api_client.dart # Connects to FastAPI for AI categorizer & sync
    │   │   ├── db_helper.dart  # Local sqlite database (sqflite) connectivity
    │   │   └── sms_service.dart# intercepter that hooks telephony SMS broadcasts
    │   ├── screens/
    │   │   ├── dashboard_screen.dart     # Displays metrics cards & budgets
    │   │   ├── expense_entry_screen.dart # Form fields and text areas
    │   │   ├── reports_screen.dart       # Integrates fl_chart pie chart
    │   │   ├── budget_screen.dart        # Budgets thresholds manager
    │   │   ├── search_screen.dart        # NLP and keyword matches listings
    │   │   └── settings_screen.dart      # Custom configs (theme, keys)
    │   └── main.dart           # App bootstrapper (requests SMS permissions)
    └── pubspec.yaml            # Flutter packages config
```

---

## 🚀 How to Run the Interactive Web Simulator

Since the local workspace lacks a Flutter installation, we have built a **high-fidelity Android Web Simulator** served by the FastAPI backend. It allows you to simulate receiving transactional SMS messages, triggers push notifications inside a virtual Android phone frame, lets you add item descriptions, and visualizes budgets, insights, and charts dynamically.

### Prerequisite
Make sure you have Python 3.8+ installed.

### 1. Install Backend Dependencies
Navigate to the `backend/` folder and install packages:
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the FastAPI Server
From the `backend/` folder, run:
```bash
python -m uvicorn main:app --reload
```
*Note: The server will start running on [http://localhost:8000](http://localhost:8000).*

### 3. Launch the Simulator
Open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

---

## 📱 Testing the Core Workflow

Once you open the Web Simulator at `http://localhost:8000`:

1. **Incoming SMS Simulation**: On the right-hand panel, select a preset bank SMS (e.g. `"Rs. 850 debited via UPI to DMART"`) and click **Send Mock SMS to Phone**.
2. **Push Notification Alert**: Look at the top of the simulated Android screen. A notification will appear: `₹850 spent at DMART. What did you buy? [Add Items] [Skip]`.
3. **Expense Entry & AI splitting**:
   - Click **Add Items**.
   - In the text area, type a list of items:
     ```
     Tea
     Sugar
     Rice
     Soap
     ```
   - Click **Save Expense**. The backend's AI categorization engine (running a local rule-based system or Gemini if API key is set) will parse and place each item into its respective category (Groceries) and unique subcategories.
4. **Dashboard & Budgets**: The dashboard metric cards (Today's, Weekly, Monthly total spent) will update, and the Category Budget progress bars will advance.
5. **Reports Tab**: Click "Reports" on the bottom navigation bar to inspect interactive doughnut, bar, and trend line charts rendering category shares.
6. **Search Tab**: Type a natural query like `"groceries in June"` or `"Amazon above 500"` to verify search compiled filters.

---

## 🛠️ Configuring the Gemini API Key

By default, the application runs on a robust **local fallback rules engine** which parses SMS texts and categorizes common grocery, travel, billing, dining, and nutrition items offline. 

To enable full LLM-based categorization and AI observations:
1. Go to the **Settings** tab (gear icon) on the bottom navigation bar of the simulator.
2. Enter your **Gemini API Key** in the input field. It will automatically save to settings.
3. Subsequent categorizations and insights will utilize Gemini model endpoints.
