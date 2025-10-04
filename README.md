CFO Copilot (Streamlit)

CFO Copilot is a small Streamlit app that answers common FP&A questions from monthly CSVs and returns text + charts. It supports revenue vs. budget, gross margin %, Opex breakdown, EBITDA proxy, and cash runway. Optional: export a short PDF.

Features

Intent-based agent:
Revenue (USD): actual vs budget
Gross Margin %: (Revenue – COGS) / Revenue
Opex total (USD): grouped by Opex:* categories
EBITDA (proxy): Revenue – COGS – Opex
Cash runway: latest cash ÷ avg monthly net burn (last 3 months)
Plotly charts inline in Streamlit
Optional export to PDF (Revenue vs Budget trend + Opex breakdown)
Project Structure

cfo-copilot/
  app.py
  requirements.txt
  README.md
  agent/
    __init__.py
    data.py
    agent.py
  fixtures/
    actuals.csv
    budget.csv
    fx.csv
    cash.csv
  tests/
    test_metrics.py
    conftest.py   # optional; helps pytest find the package
Data Format

Place 4 files under a data directory (default fixtures/, or set in sidebar / env var):

actuals.csv (monthly actuals by entity/account)
budget.csv (monthly budget by entity/account)
fx.csv (currency exchange rates to USD)
cash.csv (monthly cash balances)
Flexible column detection:

Month/date: month or date (any parseable date; normalized to month-start)
Account: account_category, account, or similar (e.g., Revenue, COGS, Opex:Marketing)
Amount: amount (or first numeric column)
Currency: currency (defaults to USD if missing)
fx.csv should include USD rates by month:

Columns like month, currency, and rate_to_usd (or any numeric column the loader can detect)
Tip: Ask for months present in your data (e.g., “January 2023”) if your CSVs don’t have 2025 dates.

Setup

cd /Users/yashaswipatki/Downloads/cfo-copilot
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
Run the App

# ensure the streamlit you're running is from the venv
which streamlit
streamlit run app.py
In the sidebar, set Data directory (e.g., /Users/yashaswipatki/Downloads/cfo-copilot/fixtures).
Sample questions:
“What was January 2023 revenue vs budget in USD?”
“Show Gross Margin % trend for the last 3 months.”
“Break down Opex by category for January 2023.”
“What is our cash runway right now?”
Optional: Export PDF

The PDF button generates 1–2 pages (Revenue trend and Opex breakdown).

Requires reportlab and kaleido:
pip install reportlab kaleido
If you installed these after the app started, stop and restart Streamlit.

Tests

Minimal smoke test for metrics:

PYTHONPATH=. pytest -q
# or ensure tests/conftest.py exists, then:
pytest -q

Record screen (QuickTime on macOS): https://drive.google.com/file/d/1fo2Dlzm8fRH6LMIVDmXmxa-WOQJ4wC1x/view?usp=sharing
