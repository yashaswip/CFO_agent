from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import plotly.express as px

# Support both package import and direct script execution
try:
	from .data import DataStore
except ImportError:
	import os, sys
	sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	from agent.data import DataStore


@dataclass
class AgentResponse:
	text: str
	figure: Optional["plotly.graph_objs.Figure"] = None


class CFOAgent:
	def __init__(self, store: DataStore):
		self.store = store

	def answer(self, question: str) -> AgentResponse:
		intent, params = self._classify(question)

		if intent == "revenue_vs_budget":
			month_text = params.get("month_text")
			df, meta = self.store.revenue_vs_budget(month_text)
			fig = px.bar(
				df,
				x="type",
				y="amount_usd",
				color="type",
				title=f"Revenue: Actual vs Budget ({meta['month'].strftime('%b %Y')})",
			)
			fig.update_yaxes(tickformat="$,.0f")
			variance_pct = meta["variance_pct"]
			variance_pct_str = f"{variance_pct*100:.1f}%" if variance_pct is not None else "n/a"
			text = (
				f"Revenue in {meta['month'].strftime('%B %Y')}: "
				f"Actual ${meta['actual']:,.0f} vs Budget ${meta['budget']:,.0f} "
				f"(Variance ${meta['variance']:,.0f}, {variance_pct_str})."
			)
			return AgentResponse(text=text, figure=fig)

		if intent == "gross_margin_trend":
			months = params.get("months", 3)
			end_text = params.get("end_text")
			trend = self.store.gross_margin_pct_trend(months=months, end_month_text=end_text)
			if trend.empty:
				return AgentResponse(text="No data available for Gross Margin % trend.")
			fig = px.line(
				trend,
				x="month",
				y="gross_margin_pct",
				title=f"Gross Margin % Trend (last {months} months)",
				markers=True,
			)
			fig.update_yaxes(tickformat=".0%")
			latest = trend.iloc[-1]
			text = f"Latest Gross Margin %: {latest['gross_margin_pct']*100:.1f}% for {latest['month'].strftime('%b %Y')}."
			return AgentResponse(text=text, figure=fig)

		if intent == "opex_breakdown":
			month_text = params.get("month_text")
			df = self.store.opex_breakdown(month_text)
			if df.empty:
				return AgentResponse(text="No Opex data for that period.")
			fig = px.pie(df, names="category", values="amount_usd", title="Opex Breakdown")
			text = f"Opex breakdown for {(self.store._month_from_text(month_text) or self.store.get_latest_month()).strftime('%B %Y')}."
			return AgentResponse(text=text, figure=fig)

		if intent == "cash_runway":
			lm, runway, extra = self.store.cash_runway_months()
			if runway is None:
				if extra.get("avg_burn") in (None, 0.0):
					txt = "No burn detected; company appears profitable or break-even. Runway is not applicable."
				else:
					txt = "Runway could not be computed due to missing data."
				return AgentResponse(text=txt)
			text = (
				f"Cash runway: {runway:.1f} months based on last cash ${extra['last_cash']:,.0f} "
				f"and avg monthly burn ${extra['avg_burn']:,.0f}. (Cash as of {lm.strftime('%b %Y')})"
			)
			return AgentResponse(text=text)

		return AgentResponse(
			text="I can help with: Revenue vs Budget, Gross Margin % trend, Opex breakdown, Cash runway."
		)

	def _classify(self, question: str) -> Tuple[str, Dict[str, Any]]:
		q = question.lower()
		month_text = self._extract_month_text(question)
		months = None
		m = re.search(r"last\s+(\d+)\s+months?", q)
		if m:
			months = int(m.group(1))

		if ("revenue" in q and "budget" in q) or "vs budget" in q:
			return "revenue_vs_budget", {"month_text": month_text}
		if "gross" in q and "margin" in q:
			return "gross_margin_trend", {"months": months or 3, "end_text": month_text}
		if "opex" in q and ("breakdown" in q or "by category" in q or "categories" in q):
			return "opex_breakdown", {"month_text": month_text}
		if "cash" in q and "runway" in q:
			return "cash_runway", {}
		return "unknown", {}

	def _extract_month_text(self, text: str) -> Optional[str]:
		month_names = "(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
		regexes = [
			rf"{month_names}\s+\d{{4}}",
			r"\d{4}[-/]\d{1,2}",
			r"\d{1,2}[-/]\d{4}",
		]
		for r in regexes:
			m = re.search(r, text, flags=re.IGNORECASE)
			if m:
				return m.group(0)
		if re.search(r"\b(this|current|now)\b.*\bmonth\b", text, flags=re.IGNORECASE):
			return None
		return None