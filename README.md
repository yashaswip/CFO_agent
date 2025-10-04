CFO Copilot
===========

CFO Copilot is a lightweight Streamlit app that helps finance teams answer common FP&A questions from monthly CSV data. It generates textual insights and interactive charts, with optional PDF export.

Features
--------

- Intent-based analysis:
  - Revenue (USD): Actual vs. Budget
  - Gross Margin %: (Revenue – COGS) / Revenue
  - Opex total (USD): Grouped by Opex categories
  - EBITDA (proxy): Revenue – COGS – Opex
  - Cash Runway: Latest cash ÷ Avg monthly net burn (last 3 months)
- Interactive Plotly charts inline in Streamlit
- Optional PDF export for Revenue trend and Opex breakdown

Project Structure
-----------------

cfo-copilot/
├── app.py
├── requirements.txt
├── README.md
├── agent/
│   ├── __init__.py
│   ├── agent.py
│   └── data.py
├── fixtures/
│   ├── actuals.csv
│   ├── budget.csv
│   ├── fx.csv
│   └── cash.csv
└── tests/
    ├── test_metrics.py
    └── conftest.py

Data Format
-----------

Place CSVs under a data directory (default: fixtures/) or configure via sidebar/env var.

Required CSVs:

1. actuals.csv – Monthly actuals by entity/account
2. budget.csv – Monthly budget by entity/account
3. fx.csv – Currency exchange rates to USD
4. cash.csv – Monthly cash balances

Flexible Column Detection:

- Month/Date: month or date (normalized to month-start)
- Account: account_category, account, etc.
- Amount: amount (or first numeric column)
- Currency: Defaults to USD if missing

fx.csv example columns: month, currency, rate_to_usd

Setup
-----

cd /Users/yashaswipatki/Downloads/cfo-copilot
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

Run the App
-----------

which streamlit  # ensure using venv version
streamlit run app.py

Set your data directory in the sidebar (e.g., /Users/yashaswipatki/Downloads/cfo-copilot/fixtures)

Sample Questions:

- What was January 2023 revenue vs budget in USD?
- Show Gross Margin % trend for the last 3 months.
- Break down Opex by category for January 2023.
- What is our cash runway right now?

Optional: Export PDF
--------------------

Generates 1–2 pages (Revenue trend and Opex breakdown).

pip install reportlab kaleido

Restart Streamlit if installed after app launch.

Tests
-----

Minimal smoke test:

PYTHONPATH=. pytest -q

or with tests/conftest.py:

pytest -q

Demo
----

Screen recording (QuickTime on macOS):  
https://drive.google.com/file/d/1fo2Dlzm8fRH6LMIVDmXmxa-WOQJ4wC1x/view?usp=sharing


