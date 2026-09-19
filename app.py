import os
import re
import requests
import pandas as pd
import streamlit as st
from openai import OpenAI

MONDAY_API_URL = "https://api.monday.com/v2"
AI_BASE_URL = "https://api.monday.com/platform-ai-gateway/openai/v1"


def get_secret(key):
    """Read configuration from environment variables or Streamlit secrets."""
    return os.getenv(key) or st.secrets.get(key)


MONDAY_API_TOKEN = get_secret("MONDAY_API_TOKEN")
DEALS_BOARD_ID = get_secret("MONDAY_DEALS_BOARD_ID")
WORK_ORDERS_BOARD_ID = get_secret("MONDAY_WORK_ORDERS_BOARD_ID")


# -----------------------------
# MONDAY DATA
# -----------------------------
def get_board_data(board_id):
    query = """
    query ($board_id: ID!) {
        boards(ids: [$board_id]) {
            id
            name
            columns { id title type }
            items_page(limit: 500) {
                items {
                    id
                    name
                    column_values { id text value }
                }
            }
        }
    }
    """
    response = requests.post(
        MONDAY_API_URL,
        headers={
            "Authorization": MONDAY_API_TOKEN,
            "Content-Type": "application/json",
        },
        json={"query": query, "variables": {"board_id": board_id}},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if "errors" in result:
        raise RuntimeError(result["errors"])
    boards = result.get("data", {}).get("boards", [])
    if not boards:
        raise RuntimeError(f"No Monday.com board found for ID {board_id}.")
    return boards[0]


def board_to_dataframe(board):
    column_map = {column["id"]: column["title"] for column in board["columns"]}
    rows = []
    for item in board["items_page"]["items"]:
        row = {"Item Name": item["name"]}
        for column in item["column_values"]:
            title = column_map.get(column["id"], column["id"])
            row[title] = column.get("text") or ""
        rows.append(row)
    return normalize_dataframe(pd.DataFrame(rows))


def normalize_dataframe(df):
    """Normalize common text, missing-value, date and numeric representations."""
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c).strip()) for c in df.columns]

    missing_tokens = {"", "-", "--", "N/A", "NA", "n/a", "na", "NULL", "null", "None", "none"}
    for col in df.columns:
        # Strip whitespace and standardize common missing markers.
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace(list(missing_tokens), pd.NA)

        name = col.lower()
        if "date" in name or "deadline" in name:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().any():
                df[col] = parsed.dt.strftime("%Y-%m-%d")

        numeric_hint = any(
            key in name
            for key in ["value", "amount", "revenue", "receivable", "invoice", "billing", "probability", "quantity"]
        )
        if numeric_hint:
            cleaned = (
                df[col].astype("string")
                .str.replace(r"[₹$€£,]", "", regex=True)
                .str.replace("%", "", regex=False)
                .str.strip()
            )
            numeric = pd.to_numeric(cleaned, errors="coerce")
            if numeric.notna().any():
                df[col] = numeric
    return df


def dataframe_quality(df):
    missing_cells = int(df.isna().sum().sum())
    return {"rows": len(df), "columns": len(df.columns), "missing_cells": missing_cells}


# -----------------------------
# DETERMINISTIC BUSINESS METRICS
# -----------------------------
def exact_count_answer(question, deals_df, work_orders_df):
    """Handle simple exact-count questions without relying on LLM arithmetic."""
    q = question.lower().strip()
    asks_count = any(x in q for x in ["how many", "count of", "number of", "total number"])
    if not asks_count:
        return None

    if "work order" in q or "work orders" in q:
        if "status" in q:
            return None
        return f"There are **{len(work_orders_df)} work orders** currently loaded from the live Monday.com Work Orders board."

    if "deal" in q or "deals" in q:
        # If the question explicitly filters by a status, let the LLM use the board context.
        if "status" in q or "open" in q or "won" in q or "lost" in q or "dead" in q:
            return None
        return f"There are **{len(deals_df)} deals** currently loaded from the live Monday.com Deals board."

    return None


# -----------------------------
# AI
# -----------------------------
def ask_ai(question, context):
    client = OpenAI(api_key=MONDAY_API_TOKEN, base_url=AI_BASE_URL)
    system_prompt = """
You are a Business Intelligence Agent for Skylark Drones.

Answer founder-level business questions using ONLY the live Monday.com data in the context.

Rules:
1. Do not invent data.
2. Distinguish the Deals board from the Work Orders board.
3. Use the normalized dates, numbers and text supplied in the context.
4. Clearly mention when information is missing or incomplete.
5. Mention important data-quality caveats before making conclusions affected by them.
6. Give concise, business-friendly answers with headings/bullets when useful.
7. Use exact numbers and percentages when supported by the data.
8. If a question is broad or ambiguous, DO NOT guess the intended scope.
   For example, questions such as "What is the performance?",
   "How is the business doing?", or "What is the status?"
   must trigger a clarification question.
   Ask whether the user means Deals, Work Orders, or both,
   and what metric or aspect they want.
9. For revenue/pipeline questions, use the Deal Value field when available and state the field used.
10. For operational questions, use Work Orders fields such as execution status, billing/collection status and amount receivable when available.
11. When useful, provide actionable business insights..
"""
    response = client.chat.completions.create(
        model="monday-fast",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"QUESTION:\n{question}\n\nBUSINESS DATA:\n{context}"},
        ],
        temperature=0.1,
        max_tokens=1200,
    )
    return response.choices[0].message.content


# -----------------------------
# APP
# -----------------------------
st.set_page_config(page_title="Skylark BI Agent", page_icon="🚁", layout="wide")
st.title("🚁 Skylark Drones — Business Intelligence Agent")
st.caption("AI-powered founder-level insights from Monday.com")

if not MONDAY_API_TOKEN:
    st.error("MONDAY_API_TOKEN is missing.")
    st.stop()
if not DEALS_BOARD_ID or not WORK_ORDERS_BOARD_ID:
    st.error("Monday.com board IDs are missing.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    deals_board = get_board_data(DEALS_BOARD_ID)
    work_orders_board = get_board_data(WORK_ORDERS_BOARD_ID)
    deals_df = board_to_dataframe(deals_board)
    work_orders_df = board_to_dataframe(work_orders_board)
except Exception as e:
    st.error(f"Could not load Monday.com data: {e}")
    st.stop()

with st.sidebar:
    st.header("📊 Live Data")
    st.metric("Deals", len(deals_df))
    st.metric("Work Orders", len(work_orders_df))
    st.divider()
    st.write("**Connected Boards**")
    st.write(f"• {deals_board['name']}")
    st.write(f"• {work_orders_board['name']}")
    st.divider()
    st.write("**Data Quality**")
    st.write(f"Deals missing cells: **{dataframe_quality(deals_df)['missing_cells']}**")
    st.write(f"Work Orders missing cells: **{dataframe_quality(work_orders_df)['missing_cells']}**")
    st.caption("Data is fetched live from Monday.com for each app load.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input("Ask a founder-level business question...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    deals_context = deals_df.to_csv(index=False)
    work_orders_context = work_orders_df.to_csv(index=False)
    context = f"""
DEALS BOARD: {deals_board['name']}
-----------------------------
{deals_context}

WORK ORDERS BOARD: {work_orders_board['name']}
-------------------------------------
{work_orders_context}
"""

    with st.chat_message("assistant"):
        with st.spinner("Analyzing live Monday.com data..."):
            try:
                answer = exact_count_answer(question, deals_df, work_orders_df)
                if answer is None:
                    answer = ask_ai(question, context)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_message = f"Error while generating answer: {e}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
