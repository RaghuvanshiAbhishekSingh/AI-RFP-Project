# Agentic RFP Evaluation and Supplier Ranking

Streamlit application for evidence-grounded supplier RFP evaluation. An LLM evaluates one proposal at a time; Python validates its response and deterministically calculates benchmarks, peer performance, and final ranks.

## Run locally

```bash
python3 -m pip install -r requirements.txt
python3 -m scripts.init_db
python3 -m scripts.generate_sample_pdfs
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

The sample proposals are fictional and will be generated under `sample_rfps/`.

## Architecture

See [architecture.md](architecture.md). The main flow is:

```text
upload PDFs → extract text → LLM scorecard → normalize → calculate → benchmark → rank → persist/export
```

`src/orchestrator.py` controls this sequence. The LLM is not allowed to calculate scores, benchmarks, PPI, or ranking.

## Scoring rules

```text
absolute score = Σ((criterion score / maximum) × weight)
benchmark      = maximum supplier score for a criterion
gap            = supplier score − benchmark
relative %     = 100 × supplier score / benchmark
PPI            = Σ(relative % × weight) / Σ(weight)
```

For a zero benchmark, all suppliers receive zero relative performance for that criterion. The sort order is: PPI descending, submission date ascending, experience rating descending, then supplier name ascending.

## Tests

```bash
python3 -m pytest -q
```

## Configuration and security

The default model is `gpt-4o-mini`; set `RFP_LLM_MODEL` to change it. For a Bring Your Own Key deployment, users enter an OpenAI API key in the password field in the sidebar. The key is kept only in their active Streamlit session and is never written to SQLite, exports, logs, or source files. Do not configure a shared application API key for this deployment.

For local developer convenience only, `.streamlit/secrets.toml` or `OPENAI_API_KEY` can supply a fallback key. Do not commit `.streamlit/secrets.toml` or include credentials in exports.

SQLite is suitable for the classroom app. Streamlit Community Cloud storage can be replaced between deployments, so download the completed-run JSON as the durable project artefact.

The evaluated scorecards remain in the active browser session until **Download completed run JSON (saves to SQLite)** is clicked. That click writes the run and all supplier results to `rfp_evaluation.sqlite3` before downloading the export. Download before refreshing or closing the browser tab.

Each saved supplier result includes its original uploaded PDF in the `supplier_documents` table. Before evaluation, the app compares SHA-256 fingerprints of uploaded PDFs against saved documents. If any match, it displays a confirmation dialog before creating a new evaluation run.
# AI-RFP-Project
