# Skylark Monday.com Business Intelligence Agent

AI-powered founder-level Business Intelligence agent that connects to two live Monday.com boards — **Deals** and **Work Orders** — and answers business questions through a conversational Streamlit interface.

## 1. What the prototype does

- Reads the Deals and Work Orders boards dynamically from Monday.com using the GraphQL API.
- Keeps the integration read-only: the app only queries board data.
- Normalizes common whitespace, missing-value markers, dates and numeric business fields before analysis.
- Shows live row counts and missing-cell counts in the sidebar.
- Answers founder-level questions with the Monday AI Gateway through an OpenAI-compatible client.
- Uses deterministic handling for simple total-count questions so basic counts do not depend on LLM arithmetic.
- Prompts the AI to identify missing data, ambiguity and data-quality caveats.
- Provides business-friendly summaries and actionable next steps when supported by the data.
- Handles Monday API and AI-generation failures with visible error messages.

## 2. Architecture

```text
                 ┌───────────────────────┐
                 │      Streamlit UI     │
                 │  Conversational Chat  │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │  Monday.com GraphQL   │
                 │      Read-only API    │
                 └───────────┬───────────┘
                             │
                  Deals + Work Orders
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Pandas Normalization  │
                 │ dates / numbers /     │
                 │ missing values/text  │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │  Business Context     │
                 │  + deterministic      │
                 │  simple metrics       │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Monday AI Gateway     │
                 │ monday-fast model     │
                 └───────────┬───────────┘
                             │
                             ▼
                 ┌───────────────────────┐
                 │ Founder-level answer  │
                 │ + caveats + next step │
                 └───────────────────────┘
```

## 3. Tech stack and why it was selected

| Technology | Purpose | Reason |
|---|---|---|
| Python | Core application | Fast to develop and strong data/AI ecosystem |
| Streamlit | Web UI and hosting | Simple conversational interface and quick deployment |
| Requests | Monday GraphQL calls | Lightweight HTTP client for the read-only API |
| Pandas | Data handling and normalization | Convenient tabular transformations and data-quality checks |
| Monday.com GraphQL API | Source of truth | Dynamic access to the required Deals and Work Orders boards |
| Monday AI Gateway | LLM reasoning | Uses the same Monday authentication flow and provides an OpenAI-compatible interface |
| OpenAI Python SDK | AI client | Simple client for the OpenAI-compatible Monday endpoint |

## 4. Monday.com configuration

The prototype expects these three configuration values:

```text
MONDAY_API_TOKEN=your_monday_personal_api_token
MONDAY_DEALS_BOARD_ID=5031418967
MONDAY_WORK_ORDERS_BOARD_ID=5031419364
```

The board IDs above correspond to the prototype's **Skylark - Deals** and **Skylark - Work Orders** boards. Do not put the API token in source code or commit it to GitHub.

### Local setup

Create a `.env` file locally (and keep it ignored by Git):

```text
MONDAY_API_TOKEN=YOUR_TOKEN
MONDAY_DEALS_BOARD_ID=5031418967
MONDAY_WORK_ORDERS_BOARD_ID=5031419364
```

Install dependencies and run:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

If your local Streamlit version does not load `.env` automatically, set the same three variables in the shell environment or use Streamlit secrets.

### Streamlit Cloud

In the deployed app, open **Settings → Secrets** and add:

```toml
MONDAY_API_TOKEN = "YOUR_TOKEN"
MONDAY_DEALS_BOARD_ID = "5031418967"
MONDAY_WORK_ORDERS_BOARD_ID = "5031419364"
```

Never paste a real token into this README, GitHub, screenshots, or the source code.

## 5. Data-quality handling

The app explicitly handles common quality issues before sending data to the AI layer:

- Trims whitespace in column names and text values.
- Converts common placeholders such as `N/A`, `NA`, `null`, `None`, `-` and blank cells to missing values.
- Attempts to normalize columns containing date/deadline terms to `YYYY-MM-DD`.
- Attempts to normalize common business numeric fields such as value, amount, revenue, receivable, invoice, billing, probability and quantity.
- Displays missing-cell counts for both boards.
- Instructs the AI to call out missing/incomplete information instead of inventing values.

The prototype is intentionally read-only and does not modify the Monday.com boards.

## 6. Example founder questions

- How many deals are currently in the Deals board?
- What is the current pipeline health?
- Which sectors have the strongest deal activity?
- What operational issues are visible from the Work Orders board?
- How much receivable amount is outstanding?
- Which work orders have billing or collection concerns?
- Compare the commercial pipeline with current operational workload.
- What should leadership pay attention to next?

For ambiguous questions, the agent is instructed to ask for clarification rather than inventing assumptions.

## 7. Limitations

- The current GraphQL query reads up to 500 items per board per request. A production version should add pagination for larger boards.
- The prototype uses the available board fields and does not create a separate warehouse or semantic layer.
- LLM-generated narrative should be treated as an interpretation of the supplied data; deterministic calculations are preferred for simple exact counts.
- A production system could add authentication/role-based access, automated tests, richer cross-board joins, caching and a dedicated BI metrics layer.

## 8. Project structure

```text
skylark-monday-bi-agent/
├── app.py
├── requirements.txt
├── README.md
├── DECISION_LOG.md
└── .gitignore
```

## 9. Security

Do not commit `.env`, Streamlit secrets, API tokens or other credentials. If a token is accidentally exposed, revoke/regenerate it in Monday.com and update the deployment secret.

## 10. Submission checklist

- [x] Hosted conversational prototype
- [x] Live Monday.com Deals integration
- [x] Live Monday.com Work Orders integration
- [x] Read-only data access
- [x] Data-quality checks and caveats
- [x] Decision Log
- [x] README with architecture and setup instructions
- [x] Source-code ZIP can be generated from the repository contents
