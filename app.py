from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import streamlit as st

from src.config import Settings
from src.database import (active_criteria, add_reviewer_note, all_criteria, complete_run, document_sha256,
    find_saved_documents, initialize_database, list_completed_runs, list_reviewer_notes, list_run_documents,
    load_document, load_run, replace_criteria)
from src.llm import OpenAIEvaluator
from src.orchestrator import evaluate_batch
from src.reporting import leaderboard_csv, report_pdf
from src.schemas import SupplierInput

st.set_page_config(page_title="RFP Compass", page_icon="🧭", layout="wide")
st.markdown("""<style>.stApp{background:#f7f9fc}.block-container{max-width:1280px;padding-top:2rem}h1{color:#16324f}[data-testid='stMetric']{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:12px}.hero{background:linear-gradient(120deg,#16324f,#256d85);padding:24px 28px;border-radius:18px;color:white;margin-bottom:20px}.hero h1{color:white;margin:0}.hero p{margin:6px 0 0;opacity:.9}</style>""", unsafe_allow_html=True)

def app_settings() -> Settings:
    base = Settings()
    secret_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st, "secrets") else None
    return Settings(database_path=base.database_path,
        openai_api_key=st.session_state.get("byok_openai_api_key") or secret_key or base.openai_api_key,
        llm_model=st.session_state.get("selected_model", base.llm_model),
        max_pdf_bytes=base.max_pdf_bytes, max_document_characters=base.max_document_characters)

with st.sidebar:
    st.header("Bring your own key")
    st.text_input("OpenAI API key", type="password", key="byok_openai_api_key", placeholder="sk-…", help="Session-only. Never saved in SQLite or exports.")
    st.text_input("Model", key="selected_model", value="gpt-4o-mini")
    if st.button("Clear API key"):
        st.session_state["byok_openai_api_key"] = ""
        st.rerun()
    st.caption("Your key is used only for this session's proposal evaluations.")

settings = app_settings()
initialize_database(settings.database_path)

def persist_pending_run() -> None:
    run_id, results, inputs = (st.session_state.get("rfp_run_id"), st.session_state.get("rfp_pending_results"), st.session_state.get("rfp_pending_inputs"))
    if run_id and results and inputs and not st.session_state.get("rfp_run_saved"):
        complete_run(settings.database_path, run_id, results, inputs)
        st.session_state["rfp_run_saved"] = True

def run_evaluation(suppliers: list[SupplierInput]) -> None:
    with st.spinner("Reading proposals, grounding evidence, and calculating the leaderboard…"):
        run_id, ranked = evaluate_batch(suppliers, settings, OpenAIEvaluator(settings).evaluate)
    st.session_state.update(rfp_run_id=run_id, rfp_pending_results=ranked, rfp_pending_inputs=suppliers, rfp_run_saved=False)
    st.success("Evaluation complete. Save or download the results below.")

@st.dialog("This PDF was evaluated before")
def confirm_rerun(duplicates: list[dict[str, object]]) -> None:
    st.write("These uploaded PDFs match saved documents:")
    for item in duplicates:
        st.write(f"• **{item['file_name']}** — {item['supplier_name']} ({item['created_at']})")
    if st.button("Rerun evaluation", type="primary"):
        st.session_state["confirmed_inputs"] = st.session_state.pop("duplicate_inputs")
        st.session_state.pop("duplicates", None)
        st.rerun()
    if st.button("Cancel"):
        st.session_state.pop("duplicate_inputs", None)
        st.session_state.pop("duplicates", None)
        st.rerun()

def result_rows(results: list[dict[str, object]]) -> list[dict[str, object]]:
    return [{"Rank": row["final_rank"], "Supplier": row["supplier_name"], "Absolute score": f"{float(row['absolute_score']):.2f}", "PPI": f"{float(row['ppi']):.2f}", "Submission date": row["submission_date"], "Experience": row["experience_rating"]} for row in results]

def render_result_dashboard(run: dict[str, object], results: list[dict[str, object]], saved: bool) -> None:
    top = results[0]
    a, b, c, d = st.columns(4)
    a.metric("Leading supplier", top["supplier_name"]); b.metric("Top PPI", f"{float(top['ppi']):.2f}"); c.metric("Suppliers", len(results)); d.metric("Run status", "Saved" if saved else "Pending save")
    st.subheader("Leaderboard")
    st.dataframe(result_rows(results), use_container_width=True, hide_index=True)
    st.subheader("Side-by-side comparison")
    st.bar_chart({row["supplier_name"]: float(row["ppi"]) for row in results}, horizontal=True)
    selected = st.selectbox("Open supplier scorecard", results, format_func=lambda row: f"#{row['final_rank']} — {row['supplier_name']}", key=f"scorecard-{run['rfp_run_id']}")
    st.write(selected.get("overall_summary") or "No overall summary supplied.")
    st.dataframe([{ "Criterion": item["criterion_id"], "Score": item["score"], "Benchmark": item["benchmark"], "Gap": item["gap"], "Relative %": item["relative_percent"], "Weight": item["weight"], "Evidence": item["evidence"], "Justification": item["justification"]} for item in selected["criteria"]], use_container_width=True, hide_index=True)
    if selected.get("warnings"): st.warning("\n".join(selected["warnings"]))
    st.caption(selected.get("ranking_explanation", ""))
    if saved:
        source = load_document(settings.database_path, str(run["rfp_run_id"]), str(selected["supplier_name"]))
        if source: st.download_button("Download original proposal PDF", source["document_bytes"], source["file_name"], "application/pdf")
        st.subheader("Reviewer notes")
        with st.form(f"review-{run['rfp_run_id']}-{selected['supplier_name']}", clear_on_submit=True):
            reviewer = st.text_input("Reviewer name"); recommendation = st.selectbox("Recommendation", ["Shortlist", "Review further", "Do not shortlist"]); note = st.text_area("Decision note")
            if st.form_submit_button("Save review note"):
                try:
                    add_reviewer_note(settings.database_path, str(run["rfp_run_id"]), str(selected["supplier_name"]), reviewer, recommendation, note)
                    st.success("Review note saved.")
                except ValueError as exc: st.error(str(exc))
        notes = list_reviewer_notes(settings.database_path, str(run["rfp_run_id"]), str(selected["supplier_name"]))
        if notes: st.dataframe(notes, use_container_width=True, hide_index=True)

st.markdown("""<div class='hero'><h1>RFP Compass</h1><p>Evidence-grounded supplier evaluation with transparent, repeatable rankings.</p></div>""", unsafe_allow_html=True)
evaluate_tab, saved_tab, criteria_tab = st.tabs(["Evaluate proposals", "Saved dashboard", "Criteria manager"])

with evaluate_tab:
    criteria = active_criteria(settings.database_path)
    with st.expander("Active evaluation criteria", expanded=False): st.dataframe([{ "Criterion": item.name, "Description": item.description, "Weight": f"{item.weight}%", "Max": item.max_score} for item in criteria], use_container_width=True, hide_index=True)
    uploads = st.file_uploader("Upload supplier RFP PDFs", type=["pdf"], accept_multiple_files=True)
    supplier_inputs: list[SupplierInput] = []
    for index, file in enumerate(uploads or []):
        with st.container(border=True):
            st.caption(file.name); col1, col2, col3 = st.columns(3)
            name = col1.text_input("Supplier", value=file.name.rsplit(".", 1)[0].replace("_", " ").title(), key=f"name-{index}")
            submitted = col2.date_input("Submission date", value=date.today(), key=f"date-{index}")
            experience = col3.number_input("Experience (0–10)", min_value=0.0, max_value=10.0, value=5.0, key=f"exp-{index}")
            supplier_inputs.append(SupplierInput(supplier_name=name, submission_date=submitted, experience_rating=Decimal(str(experience)), document_name=file.name, document_bytes=file.getvalue()))
    if confirmed := st.session_state.pop("confirmed_inputs", None):
        try: run_evaluation(confirmed)
        except Exception as exc: st.error(str(exc))
    if st.button("Evaluate supplier batch", type="primary", disabled=not supplier_inputs or not settings.openai_api_key):
        duplicates = find_saved_documents(settings.database_path, [document_sha256(item.document_bytes) for item in supplier_inputs])
        if duplicates: st.session_state.update(duplicates=duplicates, duplicate_inputs=supplier_inputs)
        else:
            try: run_evaluation(supplier_inputs)
            except Exception as exc: st.error(str(exc))
    if supplier_inputs and not settings.openai_api_key: st.info("Enter your OpenAI API key in the sidebar to begin.")
    if duplicates := st.session_state.get("duplicates"): confirm_rerun(duplicates)
    if run_id := st.session_state.get("rfp_run_id"):
        run, saved_results = load_run(settings.database_path, run_id); pending = st.session_state.get("rfp_pending_results", [])
        results = [item.model_dump(mode="json") for item in pending] if pending else saved_results
        if results:
            render_result_dashboard(run, results, bool(st.session_state.get("rfp_run_saved")))
            export = {"run": {**run, "status": "completed"}, "suppliers": results}
            st.download_button("Save to SQLite and download JSON", json.dumps(export, indent=2), "rfp_run.json", "application/json", on_click=persist_pending_run)

with saved_tab:
    runs = list_completed_runs(settings.database_path)
    if not runs: st.info("No saved evaluations yet.")
    else:
        chosen = st.selectbox("Choose a completed run", runs, format_func=lambda item: f"{item['created_at']} · {item['supplier_count']} suppliers · {item['rfp_run_id'][:8]}")
        saved_run, saved_results = load_run(settings.database_path, str(chosen["rfp_run_id"])); render_result_dashboard(saved_run, saved_results, True)
        with st.expander("Stored source PDFs"):
            st.dataframe([{ "Supplier": item["supplier_name"], "File": item["file_name"], "SHA-256": item["file_sha256"]} for item in list_run_documents(settings.database_path, str(chosen["rfp_run_id"]))], use_container_width=True, hide_index=True)
        export = {"run": saved_run, "suppliers": saved_results}; x, y, z = st.columns(3)
        x.download_button("Download JSON", json.dumps(export, indent=2), "rfp_run.json", "application/json")
        y.download_button("Download leaderboard CSV", leaderboard_csv(saved_results), "rfp_leaderboard.csv", "text/csv")
        z.download_button("Download summary PDF", report_pdf(saved_run, saved_results), "rfp_evaluation_report.pdf", "application/pdf")

with criteria_tab:
    st.subheader("Criteria manager"); st.caption("Changes affect new evaluations only; saved runs retain their criteria snapshot.")
    editable = st.data_editor([item.model_dump() for item in all_criteria(settings.database_path)], use_container_width=True, disabled=["criterion_id"], key="criteria-editor")
    if st.button("Save criteria changes"):
        try:
            records = editable.to_dict(orient="records") if hasattr(editable, "to_dict") else editable
            replace_criteria(settings.database_path, records); st.success("Criteria saved. New runs will use this configuration."); st.rerun()
        except ValueError as exc: st.error(str(exc))
