from __future__ import annotations
import pandas as pd
from agent.data import DataStore

def test_smoke_metrics():
	m = pd.to_datetime(["2023-01-01"])
	actuals = pd.DataFrame({
		"month": m.tolist() + m.tolist() + m.tolist() + m.tolist(),
		"account_category": ["Revenue", "COGS", "Opex:Marketing", "Opex:Admin"],
		"amount": [380000, 57000, 76000, 22800],
		"currency": ["USD"] * 4,
	})
	budget = pd.DataFrame({
		"month": m.tolist() + m.tolist() + m.tolist() + m.tolist(),
		"account_category": ["Revenue", "COGS", "Opex:Marketing", "Opex:Admin"],
		"amount": [400000, 56000, 72000, 24000],
		"currency": ["USD"] * 4,
	})
	fx = pd.DataFrame({"month": m, "currency": ["USD"], "rate_to_usd": [1.0]})
	cash = pd.DataFrame({"month": m, "amount": [1_000_000], "currency": ["USD"]})
	store = DataStore._from_dataframes(actuals, budget, fx, cash)

	df, meta = store.revenue_vs_budget("2023-01")
	assert int(meta["actual"]) == 380000
	assert int(meta["budget"]) == 400000
	assert set(df["type"]) == {"Actual", "Budget"}