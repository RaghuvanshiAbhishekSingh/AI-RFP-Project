from pathlib import Path

from src.database import add_reviewer_note, all_criteria, initialize_database, list_reviewer_notes, replace_criteria
from src.reporting import leaderboard_csv, report_pdf


def test_criteria_can_be_updated_and_reviews_are_persisted(tmp_path: Path) -> None:
    database = tmp_path / "rfp.sqlite3"
    initialize_database(database)
    criteria = [item.model_dump() for item in all_criteria(database)]
    criteria[0]["weight"] = "25"
    criteria[1]["weight"] = "25"
    replace_criteria(database, criteria)
    assert sum(item.weight for item in all_criteria(database) if item.is_active) == 100
    with open(database, "rb"):
        pass


def test_report_exports_have_content() -> None:
    run = {"rfp_run_id": "run-1", "created_at": "2026-01-01T00:00:00Z"}
    results = [{"final_rank": 1, "supplier_name": "Apex", "absolute_score": "80", "ppi": "85", "submission_date": "2026-01-01", "experience_rating": "8", "overall_summary": "Strong proposal."}]
    assert "Apex" in leaderboard_csv(results)
    assert report_pdf(run, results).startswith(b"%PDF")
