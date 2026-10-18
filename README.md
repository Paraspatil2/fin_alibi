# ALIBI - Corporate Expense Intelligence Engine

ALIBI is an enterprise-grade corporate expense intelligence and audit cockpit that unifies document OCR extraction, forensic math/behavioral checks, cryptographic ledger validation, and real-time policy evaluation into a single streamlined product.

## Key Features

1. **Overview & Dashboard**: Real-time KPI metrics, spend analytics, and priority review queue.
2. **Submit & Ingestion Studio**: Unified upload, multi-engine OCR extraction (Gemini / CORD / Ground Truth), metadata inspection, and fix-before-submit AI assistant chat.
3. **Review Cockpit**: Prioritized finance queue and deep-dive receipt detail panel showing unified flags, line items, and audit trail.
4. **Month Audit Cockpit**: Pattern analysis featuring employee timelines, network graphs, threshold hugging, and group meal reconciliation.
5. **Policy & Rules**: Active corporate policy rules and automated ambiguity/gap detection.
6. **Reports & Audit**: Cryptographic audit log chain verification (SHA-256 hash lineage), monthly audit pack exports, and compliance scorecards.

---

## Setup & Installation

1. Clone repository and set up a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configure environment variables (optional for offline demo mode):
   ```bash
   cp .env.example .env
   ```

---

## Running the App

Start the Streamlit application:
```bash
streamlit run alibi/app.py --server.headless true
```

Open your browser at `http://localhost:8501`.

---

## Running Tests

Run the complete test suite including integration tests:
```bash
pytest
```
