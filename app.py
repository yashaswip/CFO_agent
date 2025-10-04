from __future__ import annotations

import io
import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from agent.data import DataStore
from agent.agent import CFOAgent, AgentResponse


st.set_page_config(page_title="CFO Copilot", page_icon="💼", layout="wide")

# --------------- Sidebar: Data Directory ----------------
st.sidebar.title("Settings")
default_data_dir = os.environ.get("CFO_DATA_DIR", "fixtures")
data_dir = st.sidebar.text_input("Data directory (contains actuals/budget/fx/cash)", value=default_data_dir)
reload_clicked = st.sidebar.button("Reload data")

if "store" not in st.session_state or reload_clicked or st.session_state.get("data_dir") != data_dir:
    try:
        store = DataStore.from_directory(data_dir)
        st.session_state["store"] = store
        st.session_state["data_dir"] = data_dir
        st.sidebar.success("Data loaded.")
    except Exception as e:
        st.sidebar.error(f"Failed to load data: {e}")

store: Optional[DataStore] = st.session_state.get("store")

# --------------- Header ---------------
st.title("CFO Copilot")
st.caption("Ask questions about monthly financials. Returns text + charts.")

# --------------- Sample Prompts ---------------
with st.expander("Sample questions"):
    st.write("- What was June 2025 revenue vs budget in USD?")
    st.write("- Show Gross Margin % trend for the last 3 months.")
    st.write("- Break down Opex by category for June 2025.")
    st.write("- What is our cash runway right now?")

# --------------- Chat UI ---------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for role, content, fig in st.session_state["messages"]:
    with st.chat_message(role):
        st.write(content)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)

question = st.chat_input("Type your question...")
if question:
    with st.chat_message("user"):
        st.write(question)
    st.session_state["messages"].append(("user", question, None))

    if store is None:
        answer_text = "Data not loaded. Set a valid data directory in the sidebar."
        with st.chat_message("assistant"):
            st.write(answer_text)
        st.session_state["messages"].append(("assistant", answer_text, None))
    else:
        agent = CFOAgent(store)
        resp: AgentResponse = agent.answer(question)
        with st.chat_message("assistant"):
            st.write(resp.text)
            if resp.figure is not None:
                st.plotly_chart(resp.figure, use_container_width=True)
        st.session_state["messages"].append(("assistant", resp.text, resp.figure))

st.divider()

# --------------- Optional: PDF Export ---------------
st.subheader("Export PDF (optional)")
col1, col2 = st.columns(2)
with col1:
    months_for_revenue = st.number_input("Revenue vs Budget: months back", min_value=3, max_value=24, value=12)
with col2:
    latest_month = store.get_latest_month().strftime("%b %Y") if store else "n/a"
    st.caption(f"Latest month in data: {latest_month}")

def build_export_figures(store: DataStore, months_back: int = 12):
	end_month = store.get_latest_month()
	start_month = (end_month.to_period("M") - (months_back - 1)).to_timestamp()

	# Revenue trend (Actual vs Budget) using robust account matchers
	rev_actual = (
		store.actuals.loc[store._mask_revenue(store.actuals)]
		.groupby("month")["amount_usd"].sum().sort_index()
	)
	rev_budget = (
		store.budget.loc[store._mask_revenue(store.budget)]
		.groupby("month")["amount_usd"].sum().sort_index()
	)

	idx = rev_actual.index.union(rev_budget.index)
	df_rev = pd.DataFrame({"month": idx})
	df_rev["actual"] = df_rev["month"].map(rev_actual).fillna(0.0)
	df_rev["budget"] = df_rev["month"].map(rev_budget).fillna(0.0)
	df_rev = df_rev[(df_rev["month"] >= start_month) & (df_rev["month"] <= end_month)]

	fig1 = px.line(
		df_rev,
		x="month",
		y=["actual", "budget"],
		title=f"Revenue: Actual vs Budget (Trend, last {months_back} months)",
	)
	fig1.update_yaxes(tickformat="$,.0f")

	# Opex breakdown for latest month (handle empty gracefully)
	opex = store.opex_breakdown(end_month.strftime("%Y-%m"))
	if opex.empty:
		fig2 = px.bar(
			pd.DataFrame({"category": [], "amount_usd": []}),
			x="category",
			y="amount_usd",
			title=f"No Opex data for {end_month.strftime('%b %Y')}",
		)
	else:
		fig2 = px.pie(
			opex,
			names="category",
			values="amount_usd",
			title=f"Opex Breakdown ({end_month.strftime('%b %Y')})",
		)

	return fig1, fig2


def figures_to_pdf(figs):
    # Import here so missing deps don't crash app import
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
    except Exception as e:
        raise RuntimeError("PDF export requires reportlab. Install with: pip install reportlab") from e

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    width, height = LETTER
    for fig in figs:
        try:
            png_bytes = fig.to_image(format="png", width=1200, height=700, scale=1)
        except Exception as e:
            raise RuntimeError("Plotly image export requires kaleido. Install with: pip install -U kaleido") from e
        img_buf = io.BytesIO(png_bytes)
        img = ImageReader(img_buf)
        margin = 36
        max_w, max_h = width - 2 * margin, height - 2 * margin
        c.drawImage(img, margin, margin, width=max_w, height=max_h, preserveAspectRatio=True, anchor="c")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf

disabled = store is None
if st.button("Generate PDF", disabled=disabled):
    try:
        fig1, fig2 = build_export_figures(store, months_back=months_for_revenue)  # type: ignore[arg-type]
        pdf_bytes = figures_to_pdf([fig1, fig2])
        st.download_button("Download CFO Pack (PDF)", data=pdf_bytes, file_name="cfo_pack.pdf", mime="application/pdf")
        st.success("PDF generated.")
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
