
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, List

import numpy as np
import pandas as pd
from dateutil import parser as date_parser


def _standardize_month_column(df: pd.DataFrame, month_col_candidates: List[str]) -> pd.DataFrame:
	df = df.copy()
	lower_map = {c.lower(): c for c in df.columns}
	for cand in month_col_candidates:
		if cand in lower_map:
			col = lower_map[cand]
			series = pd.to_datetime(df[col], errors="coerce")
			df["month"] = series.dt.to_period("M").dt.to_timestamp()
			return df
	# Fallback: try parse first parsable column
	for c in df.columns:
		try:
			series = pd.to_datetime(df[c], errors="coerce")
			if series.notna().any():
				df["month"] = series.dt.to_period("M").dt.to_timestamp()
				return df
		except Exception:
			continue
	raise ValueError("Could not find or parse a month/date column in dataframe.")


def _standardize_currency_column(df: pd.DataFrame) -> pd.DataFrame:
	df = df.copy()
	lower_map = {c.lower(): c for c in df.columns}
	currency_col = None
	for cand in ["currency", "curr", "ccy"]:
		if cand in lower_map:
			currency_col = lower_map[cand]
			break
	if currency_col is None:
		df["currency"] = "USD"
	else:
		df["currency"] = df[currency_col].astype(str).str.upper().str.strip()
	return df


def _find_account_column_name(df: pd.DataFrame) -> Optional[str]:
	lower_map = {c.lower(): c for c in df.columns}
	candidates = [
		"account",
		"account_category",
		"account category",
		"category",
		"line_item",
		"line item",
		"acct",
		"name",
		"account name",
		"gl account",
		"gl_account",
	]
	for cand in candidates:
		if cand in lower_map:
			return lower_map[cand]
	for c in df.columns:
		if "account" in str(c).lower():
			return c
	return None


def _standardize_account_column(df: pd.DataFrame) -> pd.DataFrame:
	df = df.copy()
	account_col = _find_account_column_name(df)
	if account_col is None:
		df["account"] = "Unknown"
	else:
		df["account"] = df[account_col].astype(str).str.strip()
	df["account_norm"] = df["account"].astype(str).str.strip().str.lower()
	return df


def _standardize_amount_column(df: pd.DataFrame, prefer: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
	df = df.copy()
	lower_map = {c.lower(): c for c in df.columns}
	candidates = [prefer] if prefer else []
	candidates += ["amount_usd", "amount", "value", "usd", "total"]
	for cand in candidates:
		if cand and cand in lower_map:
			return df, lower_map[cand]
	# Fallback: first numeric column
	for c in df.columns:
		if pd.api.types.is_numeric_dtype(df[c]):
			return df, c
	raise ValueError("Could not detect a numeric amount column.")


def _read_csv_or_excel(path: str) -> pd.DataFrame:
	if path.lower().endswith((".xlsx", ".xls")):
		return pd.read_excel(path)
	return pd.read_csv(path)


def _resolve_file(data_dir: str, candidates: List[str]) -> str:
	for name in candidates:
		path = os.path.join(data_dir, name)
		if os.path.exists(path):
			return path
	raise FileNotFoundError(f"Could not find any of {candidates} in {data_dir}")


@dataclass
class DataStore:
	actuals: pd.DataFrame
	budget: pd.DataFrame
	fx: pd.DataFrame
	cash: pd.DataFrame

	@classmethod
	def from_directory(cls, data_dir: str) -> "DataStore":
		actuals_path = _resolve_file(data_dir, ["actuals.csv", "actuals.xlsx"])
		budget_path = _resolve_file(data_dir, ["budget.csv", "budget.xlsx"])
		fx_path = _resolve_file(data_dir, ["fx.csv", "fx.xlsx"])
		cash_path = _resolve_file(data_dir, ["cash.csv", "cash.xlsx"])

		actuals = _read_csv_or_excel(actuals_path)
		budget = _read_csv_or_excel(budget_path)
		fx = _read_csv_or_excel(fx_path)
		cash = _read_csv_or_excel(cash_path)

		return cls._from_dataframes(actuals, budget, fx, cash)

	@classmethod
	def _from_dataframes(
		cls, actuals: pd.DataFrame, budget: pd.DataFrame, fx: pd.DataFrame, cash: pd.DataFrame
	) -> "DataStore":
		actuals = actuals.copy()
		budget = budget.copy()
		fx = fx.copy()
		cash = cash.copy()

		for df in (actuals, budget, fx, cash):
			df.columns = [str(c).strip() for c in df.columns]

		# Standardize key columns
		actuals = _standardize_month_column(actuals, ["month", "date", "period"])
		budget = _standardize_month_column(budget, ["month", "date", "period"])
		fx = _standardize_month_column(fx, ["month", "date"])
		cash = _standardize_month_column(cash, ["month", "date"])

		actuals = _standardize_currency_column(actuals)
		budget = _standardize_currency_column(budget)
		fx = _standardize_currency_column(fx)
		cash = _standardize_currency_column(cash)

		actuals = _standardize_account_column(actuals)
		budget = _standardize_account_column(budget)

		# Identify amount columns
		actuals, actuals_amount_col = _standardize_amount_column(actuals)
		budget, budget_amount_col = _standardize_amount_column(budget)
		fx, fx_rate_col = _standardize_amount_column(fx, prefer="rate_to_usd")
		cash, cash_amount_col = _standardize_amount_column(cash)

		# FX merge and USD conversion
		fx_rates = fx.rename(columns={fx_rate_col: "rate_to_usd"})[["month", "currency", "rate_to_usd"]]
		for df, col in [(actuals, actuals_amount_col), (budget, budget_amount_col), (cash, cash_amount_col)]:
			df["currency"] = df["currency"].fillna("USD").replace("", "USD")
			df["currency"] = df["currency"].astype(str).str.upper().str.strip()
			df_merged = df.merge(fx_rates, on=["month", "currency"], how="left")
			mask_usd = df_merged["currency"].astype(str).str.upper() == "USD"
			df_merged.loc[mask_usd, "rate_to_usd"] = df_merged.loc[mask_usd, "rate_to_usd"].fillna(1.0)
			if df_merged["rate_to_usd"].isna().any():
				missing = df_merged[df_merged["rate_to_usd"].isna()][["month", "currency"]].drop_duplicates()
				raise ValueError(f"Missing FX rates for: {missing.to_dict(orient='records')}")
			df["amount_usd"] = df[col].astype(float) * df_merged["rate_to_usd"].astype(float)

		actuals_std = actuals[["month", "account", "account_norm", "amount_usd"]].copy()
		budget_std = budget[["month", "account", "account_norm", "amount_usd"]].copy()
		cash_std = cash[["month", "amount_usd"]].copy()

		return cls(actuals=actuals_std, budget=budget_std, fx=fx_rates, cash=cash_std)

	# --------------- Metrics -----------------

	def get_latest_month(self) -> pd.Timestamp:
		series = pd.concat([self.actuals["month"], self.budget["month"], self.cash["month"]], ignore_index=True)
		return series.max()

	def _month_from_text(self, text: Optional[str]) -> Optional[pd.Timestamp]:
		if not text:
			return None
		try:
			dt = date_parser.parse(text, default=pd.Timestamp.today().to_pydatetime(), dayfirst=False)
			return pd.Timestamp(dt).to_period("M").to_timestamp()
		except Exception:
			return None

	# ---- account matching helpers (case-insensitive + synonyms) ----

	@staticmethod
	def _mask_revenue(df: pd.DataFrame) -> pd.Series:
		s = df["account_norm"].astype(str)
		pattern = re.compile(r"(?:^revenue$|\brevenue\b|\bsales\b|\bturnover\b|\bnet revenue\b|\btotal revenue\b)", re.IGNORECASE)
		return s.str.contains(pattern, na=False)

	@staticmethod
	def _mask_cogs(df: pd.DataFrame) -> pd.Series:
		s = df["account_norm"].astype(str)
		pattern = re.compile(r"(?:^cogs$|\bcogs\b|\bcost of goods\b|\bcost of sales\b)", re.IGNORECASE)
		return s.str.contains(pattern, na=False)

	@staticmethod
	def _mask_opex(df: pd.DataFrame) -> pd.Series:
		s = df["account_norm"].astype(str)
		pattern = re.compile(r"(?:^opex|\bopex\b|\boperating exp|\boperating expenses?\b|\bexpenses?\b|\bsg&a\b|\bg&a\b|\bsga\b)", re.IGNORECASE)
		return s.str.contains(pattern, na=False)

	def _sum_revenue(self, df: pd.DataFrame, month: pd.Timestamp) -> float:
		sub = df[df["month"] == month]
		return float(sub.loc[self._mask_revenue(sub), "amount_usd"].sum())

	def _sum_cogs(self, df: pd.DataFrame, month: pd.Timestamp) -> float:
		sub = df[df["month"] == month]
		return float(sub.loc[self._mask_cogs(sub), "amount_usd"].sum())

	def _sum_opex(self, df: pd.DataFrame, month: pd.Timestamp) -> float:
		sub = df[df["month"] == month]
		return float(sub.loc[self._mask_opex(sub), "amount_usd"].sum())

	def revenue_vs_budget(self, month_text: Optional[str] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
		month = self._month_from_text(month_text) or self.get_latest_month()
		actual_rev = self._sum_revenue(self.actuals, month)
		budget_rev = self._sum_revenue(self.budget, month)
		df = pd.DataFrame({"type": ["Actual", "Budget"], "amount_usd": [actual_rev, budget_rev]})
		insights = {
			"month": month,
			"actual": float(actual_rev),
			"budget": float(budget_rev),
			"variance": float(actual_rev - budget_rev),
			"variance_pct": float((actual_rev - budget_rev) / budget_rev) if budget_rev else None,
		}
		return df, insights

	def gross_margin_pct_trend(self, months: int = 3, end_month_text: Optional[str] = None) -> pd.DataFrame:
		end_month = self._month_from_text(end_month_text) or self.get_latest_month()
		start_month = (end_month.to_period("M") - (months - 1)).to_timestamp()
		actuals = self.actuals[(self.actuals["month"] >= start_month) & (self.actuals["month"] <= end_month)].copy()
		revenue = actuals.loc[self._mask_revenue(actuals)].groupby("month")["amount_usd"].sum().sort_index()
		cogs = actuals.loc[self._mask_cogs(actuals)].groupby("month")["amount_usd"].sum().sort_index()
		idx = revenue.index.union(cogs.index)
		df = pd.DataFrame({"month": idx})
		df["revenue"] = df["month"].map(revenue).fillna(0.0)
		df["cogs"] = df["month"].map(cogs).fillna(0.0)
		df["gross_margin_pct"] = np.where(df["revenue"] != 0, (df["revenue"] - df["cogs"]) / df["revenue"], np.nan)
		return df

	def opex_breakdown(self, month_text: Optional[str] = None) -> pd.DataFrame:
		month = self._month_from_text(month_text) or self.get_latest_month()
		df = self.actuals[self.actuals["month"] == month].copy()
		if df.empty:
			return pd.DataFrame(columns=["category", "amount_usd"])
		opex = df[self._mask_opex(df)].copy()
		if opex.empty:
			return pd.DataFrame(columns=["category", "amount_usd"])
		def _extract_category(x: str) -> str:
			val = str(x)
			if ":" in val:
				prefix, rest = val.split(":", 1)
				if prefix.strip().lower().startswith("opex"):
					return rest.strip() or "Other"
			ln = val.lower()
			if "sg&a" in ln or "sga" in ln:
				return "SG&A"
			if "operating exp" in ln:
				return "Operating Expenses"
			return val
		opex["category"] = opex["account"].map(_extract_category)
		return opex.groupby("category", as_index=False)["amount_usd"].sum().sort_values("amount_usd", ascending=False)

	def ebitda(self, month_text: Optional[str] = None) -> Tuple[pd.Timestamp, float]:
		month = self._month_from_text(month_text) or self.get_latest_month()
		revenue = self._sum_revenue(self.actuals, month)
		cogs = self._sum_cogs(self.actuals, month)
		opex = self._sum_opex(self.actuals, month)
		return month, float(revenue - cogs - opex)

	def cash_runway_months(self, lookback_months: int = 3) -> Tuple[pd.Timestamp, Optional[float], Dict[str, float]]:
		last_cash_month = self.cash["month"].max()
		last_cash = float(self.cash[self.cash["month"] == last_cash_month]["amount_usd"].sum())

		all_months = sorted(self.actuals["month"].unique())
		if not all_months:
			return last_cash_month, None, {"last_cash": last_cash, "avg_burn": None, "method": "none"}
		end_month = max(all_months)
		end_idx = max(i for i, m in enumerate(all_months) if m <= end_month)
		start_idx = max(0, end_idx - (lookback_months - 1))
		window = all_months[start_idx : end_idx + 1]

		# EBITDA-based burn
		ebitdas: List[float] = []
		for m in window:
			revenue = self._sum_revenue(self.actuals, m)
			cogs = self._sum_cogs(self.actuals, m)
			opex = self._sum_opex(self.actuals, m)
			ebitdas.append(float(revenue - cogs - opex))
		burns_ebitda = [max(-v, 0.0) for v in ebitdas]
		avg_burn_ebitda = float(np.mean(burns_ebitda)) if burns_ebitda else 0.0
		if avg_burn_ebitda > 0:
			return last_cash_month, last_cash / avg_burn_ebitda, {
				"last_cash": last_cash,
				"avg_burn": avg_burn_ebitda,
				"method": "ebitda",
				"months": len(window),
			}

		# Fallback: gross burn (COGS + Opex)
		gross_burns: List[float] = []
		for m in window:
			cogs = self._sum_cogs(self.actuals, m)
			opex = self._sum_opex(self.actuals, m)
			gross_burns.append(float(max(cogs + opex, 0.0)))
		avg_burn_gross = float(np.mean(gross_burns)) if gross_burns else 0.0
		if avg_burn_gross > 0:
			return last_cash_month, last_cash / avg_burn_gross, {
				"last_cash": last_cash,
				"avg_burn": avg_burn_gross,
				"method": "gross_burn",
				"months": len(window),
			}

		return last_cash_month, None, {"last_cash": last_cash, "avg_burn": 0.0, "method": "none", "months": len(window)}