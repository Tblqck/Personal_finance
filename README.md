
# 💸 AI-Powered Personal Finance Assistant Bot

A smart **Telegram-based personal finance assistant** that uses **AI intent detection** and **automated data analytics** to help users track income, expenses, and budgets — then returns **PDF financial reports with visual insights**.

This project merges **natural language understanding**, **structured data management**, and **intelligent reporting** into one seamless system.

---

## 🧠 Overview

The **Personal Finance Assistant** listens to natural messages like:

> “I spent ₦3,200 on groceries yesterday.”  
> “Add my ₦45,000 salary income.”  
> “Show me my October spending report.”

It automatically classifies intents using a hybrid **rule-based + LLM** system and stores structured data in a local JSON database.  
At any time, users can request a **PDF report** that includes visual spending analytics, category breakdowns, and personalized insights.

The system is modular, privacy-preserving (all data is local), and built for offline-first operation.

---

## 🧩 Architecture

```

📁 finance_bot/
│
├── telegram_bot.py          # Entry point for Telegram interaction
├── chat_manager.py          # Handles chat sessions, login, and state
├── intent_finder.py         # Local + AI-based intent recognition
├── income_core.py           # Income logging logic
├── expencies_core.py        # Expense recording logic
├── finance_reports.py       # Data analysis + PDF generation
├── onboarding.py            # User onboarding and first-time setup
├── login_flow.py            # Basic user authentication flow
├── exchange_rates.py        # Live currency conversion support
├── user_data.json           # Local persistent user storage
└── requirements.txt         # Dependencies list

````

---

## 🚀 Features

### 🧭 AI Intent Recognition
- Detects user intent from natural chat messages using:
  - Local rules (e.g. “add”, “spent”, “earned”)
  - Fallback to **Mixtral-8x7B** via [OpenRouter API](https://openrouter.ai/)
- Supported intents:  
  - `add_income`  
  - `add_expense`  
  - `generate_report`  
  - `set_reminder`  
  - `general_chat`

### 💰 Income & Expense Management
- Automatically stores all transactions in `user_data.json`
- Supports custom categories and timestamps
- Maintains running totals and daily logs

### 📊 Automated PDF Analysis Reports
- Generates **rich PDF reports** via Matplotlib + ReportLab
- Includes:
  - Daily and monthly spending graphs
  - Expense distribution by category
  - Income vs. expense summary
  - Personalized commentary (“You saved 15% more than last month 🎉”)
- Each report is time-stamped and sent back via Telegram

### 💬 Multi-Channel Design
- Built around a **chat manager** that can easily extend to:
  - Telegram
  - WhatsApp (via Twilio API)
  - Web dashboard (future)
- Local session persistence for multi-user handling

### 🌍 Exchange Rate Awareness
- Integrates with real-time exchange APIs for automatic NGN/USD/GBP conversions in reports

---

## 🧾 Example User Flow

**User:**  
> I earned ₦20,000 from freelancing today.  

**Bot:**  
✅ Added ₦20,000 to your income log under *Freelance*.  

---

**User:**  
> I spent ₦3,200 on transport.  

**Bot:**  
🚗 Logged ₦3,200 under *Transport expenses*.  

---

**User:**  
> Generate my weekly report.  

**Bot:**  
📊 *[Sends a PDF file]*  
Your weekly financial summary is ready.  
- Total Income: ₦120,000  
- Total Expenses: ₦74,200  
- Savings: ₦45,800  
- Top spending category: Food (31%)  

---

## 🧮 How Reports Work

The file `finance_reports.py` analyzes data from `user_data.json` and produces visualizations:
- **Line charts** for daily trends  
- **Pie charts** for category distributions  
- **Bar charts** for monthly performance  

Each report includes automated insights like:
> “Your food spending decreased by 12% compared to last week.”  
> “You earned more income from side projects this month.”  

The system then compiles everything into a clean **PDF report**, saved locally and sent via Telegram.

---

## 🧠 Technical Stack

| Layer | Technology |
|-------|-------------|
| Language | Python 3.10 |
| Data Handling | Pandas, JSON |
| AI Model | Mixtral-8x7B (via OpenRouter API) |
| Visualization | Matplotlib |
| Report Generation | ReportLab |
| Bot Framework | python-telegram-bot |
| Exchange Rates | Free API / Custom parser |

---

## ⚙️ Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Tblqck/finance_assistant_bot.git
cd finance_assistant_bot
````

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Add Your API Keys

Create a `.env` file and set:

```
TELEGRAM_BOT_TOKEN=your_bot_token
OPENROUTER_API_KEY=your_api_key
```

### 4️⃣ Run the Bot

```bash
python telegram_bot.py
```

---

## 🔒 Privacy & Data Handling

All user financial data is stored **locally** in `user_data.json`.
No cloud storage or third-party logging — full data ownership remains with the user.

---

## 📈 Future Upgrades

* Multi-user cloud sync (Google Drive or Firestore)
* Voice-command integration
* Interactive web dashboard
* AI budgeting advisor (predict next-month expenses)

---

## ⚖️ License

**Proprietary — Contact for License**

```
Copyright (c) 2025 Abasiekeme Hanson

This repository includes proprietary code for an AI-driven personal finance assistant.
Use, modification, or redistribution without written permission is prohibited.

For collaboration or licensing, contact:
📩 Hansonabasiekeme2@gmail.com
```

---

## 👤 Author

**Abasiekeme Hanson (T. Black)**
*Data Scientist • AI Systems Engineer • Automation Specialist*

* GitHub: [Tblqck](https://github.com/Tblqck)
* Telegram: [@TBlackAI](@darcxe)
* Email: [Hansonabasiekeme2@gmail.com](mailto:Hansonabasiekeme2@gmail.com)

---

⭐ **If you like the concept, drop a star — it helps visibility and future updates.**

