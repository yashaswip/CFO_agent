# CFO Copilot

CFO Copilot is a lightweight **Streamlit app** that helps finance teams answer common FP&A questions from monthly CSV data. It generates both textual insights and interactive charts, with optional PDF export.

Demo: https://drive.google.com/file/d/1fo2Dlzm8fRH6LMIVDmXmxa-WOQJ4wC1x/view?usp=sharing
---

## Features

- **Intent-based analysis** of financial metrics:
  - **Revenue (USD)**: Actual vs. Budget  
  - **Gross Margin %**: `(Revenue – COGS) / Revenue`  
  - **Opex total (USD)**: Grouped by Opex categories  
  - **EBITDA (proxy)**: `Revenue – COGS – Opex`  
  - **Cash Runway**: `Latest cash ÷ Avg monthly net burn (last 3 months)`  

- **Interactive Plotly charts** displayed inline in Streamlit  
- **Optional PDF export** for:
  - Revenue vs Budget trend  
  - Opex breakdown  

---

## Project Structure

cfo-copilot/
├── app.py
├── requirements.txt
├── README.md
├── agent/
│ ├── init.py
│ ├── agent.py
│ └── data.py
├── fixtures/
│ ├── actuals.csv
│ ├── budget.csv
│ ├── fx.csv
│ └── cash.csv
└── tests/
├── test_metrics.py
└── conftest.py

---

## Data Format

Place your CSVs under a **data directory** (default: `fixtures/`) or configure via the sidebar or environment variable.

### Required CSVs

1. `actuals.csv` – Monthly actuals by entity/account  
2. `budget.csv` – Monthly budget by entity/account  
3. `fx.csv` – Currency exchange rates to USD  
4. `cash.csv` – Monthly cash balances  

### Flexible Column Detection

- **Month/Date**: `month` or `date` (any parseable date; normalized to month-start)  
- **Account**: `account_category`, `account`, or similar  
- **Amount**: `amount` (or first numeric column)  
- **Currency**: Defaults to USD if missing  

`fx.csv` should include USD rates by month with columns like:  
`month`, `currency`, `rate_to_usd`  

**Tip:** Ask for months present in your data if your CSVs don’t contain 2025 dates.

---

## Setup

```bash
cd /Users/yashaswipatki/Downloads/cfo-copilot
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
Run the App
which streamlit        # ensure the streamlit from venv is used
streamlit run app.py
In the sidebar, set your data directory (e.g., /Users/yashaswipatki/Downloads/cfo-copilot/fixtures).
Sample Questions
“What was January 2023 revenue vs budget in USD?”
“Show Gross Margin % trend for the last 3 months.”
“Break down Opex by category for January 2023.”
“What is our cash runway right now?”
Optional: Export PDF
The PDF export generates 1–2 pages (Revenue trend and Opex breakdown).
pip install reportlab kaleido
If installed after starting Streamlit, restart the app.
Tests
Minimal smoke test for metrics:
PYTHONPATH=. pytest -q
or with tests/conftest.py present:
pytest -q


