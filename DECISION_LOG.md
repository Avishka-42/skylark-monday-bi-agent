# Decision Log — Monday.com Business Intelligence Agent

## 1. Goal and interpretation

The goal was to build a small founder-facing BI agent that can answer conversational questions across two Monday.com boards: **Deals** and **Work Orders**. I interpreted “leadership updates” as concise executive-level information covering pipeline/commercial status, operational workload, risks or data-quality caveats, and practical next steps supported by the available data.

The prototype is read-only. Monday.com is treated as the live source of truth rather than importing the Excel files into the application itself.

## 2. Key assumptions

- The configured Deals and Work Orders boards contain the required assignment data.
- Board values available through Monday.com are authoritative for the prototype at query/load time.
- `Deal Value` is the available commercial-value field for pipeline/revenue-oriented questions when present.
- Work-order operational questions use available fields such as execution status, billing/collection status and amount receivable.
- Missing or inconsistent values should be surfaced rather than silently invented.
- A founder-facing answer should be concise and decision-oriented rather than returning a raw data dump.
- The current prototype reads up to 500 items per board in one request; larger production boards would require pagination.

## 3. Architecture decision

The implementation uses **Streamlit → Monday.com GraphQL API → Pandas normalization → business context → Monday AI Gateway → conversational response**.

**Why:** this is small enough to build and deploy quickly while still meeting the requirement for dynamic Monday.com access and a conversational interface. Pandas provides a simple place to standardize missing values, dates, numeric fields and text before the AI layer receives the data.

## 4. Technology choices and trade-offs

- **Python + Streamlit:** chosen for fast implementation of a hosted interactive prototype. Trade-off: a larger production system would benefit from a more modular backend/frontend architecture.
- **Monday GraphQL API:** chosen as the direct read-only integration. Trade-off: the prototype has API latency and currently uses a 500-item request limit rather than a full pagination/data warehouse layer.
- **Pandas:** chosen for lightweight normalization and data-quality checks. Trade-off: all analysis is performed in application memory, so a production system would need stronger scaling and caching strategies.
- **Monday AI Gateway + OpenAI SDK:** chosen because the Monday endpoint is OpenAI-compatible and can be called using the Monday credential. Trade-off: the LLM remains probabilistic, so simple exact counts are handled deterministically where practical.

## 5. Data-quality decisions

The app normalizes common missing markers, trims whitespace, standardizes date-like fields to `YYYY-MM-DD` when parseable, and converts common business numeric fields when they can be parsed safely. Missing-cell counts are displayed in the UI. The AI prompt explicitly instructs the model to identify incomplete data and avoid fabricating values.

If a question cannot be answered reliably from the available fields, the agent is instructed to ask for clarification or state the limitation.

## 6. What I would do with more time

1. Add full cursor-based pagination for boards larger than 500 items.
2. Add a deterministic BI/metrics layer for revenue, weighted pipeline, sector summaries and operational KPIs rather than relying primarily on LLM reasoning for aggregation.
3. Add robust cross-board joins using stable identifiers such as client/deal codes where available.
4. Add automated unit/integration tests for API failures, missing columns, malformed dates, numeric parsing and representative founder questions.
5. Add authentication/role-based access and structured logging for production use.
6. Improve the interface with charts and downloadable leadership summaries.

## 7. Definition of a useful leadership update

For this prototype, a useful leadership update is not a long record-by-record explanation. It should answer: **What is happening? What evidence supports it? What is uncertain or missing? What should leadership look at next?** The agent therefore emphasizes concise metrics, trends/patterns supported by the boards, explicit data-quality caveats, and actionable next steps.
