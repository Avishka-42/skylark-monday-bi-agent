import os
import requests
import pandas as pd
import streamlit as st
from openai import OpenAI

MONDAY_API_URL = "https://api.monday.com/v2"
AI_BASE_URL = "https://api.monday.com/platform-ai-gateway/openai/v1"


def get_secret(key):
    """Read config from environment (.env locally) or Streamlit secrets (cloud)."""
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
            columns {
                id
                title
                type
            }
            items_page(limit: 500) {
                items {
                    id
                    name
                    column_values {
                        id
                        text
                        value
                    }
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
        json={
            "query": query,
            "variables": {"board_id": board_id},
        },
        timeout=30,
    )

    response.raise_for_status()

    result = response.json()

    if "errors" in result:
        raise Exception(result["errors"])

    return result["data"]["boards"][0]


def board_to_dataframe(board):
    column_map = {
        column["id"]: column["title"]
        for column in board["columns"]
    }

    rows = []

    for item in board["items_page"]["items"]:
        row = {
            "Item Name": item["name"]
        }

        for column in item["column_values"]:
            title = column_map.get(column["id"], column["id"])
            row[title] = column.get("text", "")

        rows.append(row)

    return pd.DataFrame(rows)


# -----------------------------
# AI
# -----------------------------

def ask_ai(question, context):
    client = OpenAI(
        api_key=MONDAY_API_TOKEN,
        base_url=AI_BASE_URL,
    )

    system_prompt = """
You are a Business Intelligence Agent for Skylark Drones.

You answer founder-level business questions using ONLY the data
provided in the context.

Rules:
1. Do not invent data.
2. Clearly mention when information is missing.
3. Mention important data-quality caveats.
4. Give concise business-friendly answers.
5. Use numbers and percentages when supported.
6. If a question is ambiguous and cannot be answered reliably,
   ask a clarification question.
7. When useful, provide actionable business insights.
"""

    response = client.chat.completions.create(
        model="monday-fast",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": f"""
QUESTION:
{question}

BUSINESS DATA:
{context}
""",
            },
        ],
        temperature=0.1,
        max_tokens=1200,
    )

    return response.choices[0].message.content


# -----------------------------
# APP
# -----------------------------

st.set_page_config(
    page_title="Skylark BI Agent",
    page_icon="🚁",
    layout="wide",
)

st.title("🚁 Skylark Drones — Business Intelligence Agent")
st.caption("AI-powered founder-level insights from Monday.com")

if not MONDAY_API_TOKEN:
    st.error("MONDAY_API_TOKEN is missing.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []


# Load live Monday data
try:
    deals_board = get_board_data(DEALS_BOARD_ID)
    work_orders_board = get_board_data(WORK_ORDERS_BOARD_ID)

    deals_df = board_to_dataframe(deals_board)
    work_orders_df = board_to_dataframe(work_orders_board)

except Exception as e:
    st.error(f"Could not load Monday.com data: {e}")
    st.stop()


# Sidebar
with st.sidebar:
    st.header("📊 Live Data")

    st.metric("Deals", len(deals_df))
    st.metric("Work Orders", len(work_orders_df))

    st.divider()

    st.write("**Connected Boards**")
    st.write("• Skylark - Deals")
    st.write("• Skylark - Work Orders")

    st.divider()

    st.write("**Data Quality**")

    deals_missing = int(deals_df.isna().sum().sum())
    wo_missing = int(work_orders_df.isna().sum().sum())

    st.write(f"Deals missing cells: **{deals_missing}**")
    st.write(f"Work Orders missing cells: **{wo_missing}**")


# Show previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# User question
question = st.chat_input("Ask a founder-level business question...")

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Prepare context
    deals_context = deals_df.to_csv(index=False)
    work_orders_context = work_orders_df.to_csv(index=False)

    context = f"""
DEALS BOARD
-----------
{deals_context}

WORK ORDERS BOARD
-----------------
{work_orders_context}
"""

    with st.chat_message("assistant"):
        with st.spinner("Analyzing live Monday.com data..."):

            try:
                answer = ask_ai(question, context)

                st.markdown(answer)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                    }
                )

            except Exception as e:
                error_message = f"Error while generating answer: {e}"

                st.error(error_message)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )