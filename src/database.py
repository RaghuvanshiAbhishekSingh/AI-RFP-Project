from __future__ import annotations

import json
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from .schemas import Criterion, RankedSupplier, SupplierInput


DEFAULT_CRITERIA = (
    ("Technical Capability", "Architecture, integrations, scalability, and technical fit.", "30", "10"),
    ("Implementation Plan", "Timeline, milestones, staffing, and risk plan.", "20", "10"),
    ("Commercial Value", "Pricing clarity, total cost, and assumptions.", "20", "10"),
    ("Security & Compliance", "Controls, certifications, privacy, and auditability.", "20", "10"),
    ("Support & Experience", "Support model, similar projects, and references.", "10", "10"),
)


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value)!r}")


def connect(database_path: Path | str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path | str) -> None:
    with connect(database_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS evaluation_criteria (
                criterion_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE CHECK (length(trim(name)) > 0),
                description TEXT NOT NULL,
                weight REAL NOT NULL CHECK (weight >= 0 AND weight <= 100),
                max_score REAL NOT NULL CHECK (max_score > 0),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS rfp_runs (
                rfp_run_id TEXT PRIMARY KEY NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
                criteria_snapshot_json TEXT NOT NULL,
                config_json TEXT NOT NULL DEFAULT '{}',
                warnings_json TEXT NOT NULL DEFAULT '[]',
                error_message TEXT
            );
            CREATE TABLE IF NOT EXISTS supplier_results (
                rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
                supplier_name TEXT NOT NULL COLLATE NOCASE,
                submission_date TEXT NOT NULL,
                experience_rating REAL NOT NULL CHECK (experience_rating BETWEEN 0 AND 10),
                absolute_score REAL NOT NULL CHECK (absolute_score BETWEEN 0 AND 100),
                ppi REAL NOT NULL CHECK (ppi BETWEEN 0 AND 100),
                final_rank INTEGER NOT NULL CHECK (final_rank > 0),
                result_json TEXT NOT NULL,
                PRIMARY KEY (rfp_run_id, supplier_name),
                UNIQUE (rfp_run_id, final_rank)
            );
            CREATE TABLE IF NOT EXISTS supplier_documents (
                rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
                supplier_name TEXT NOT NULL COLLATE NOCASE,
                file_name TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                document_bytes BLOB NOT NULL,
                PRIMARY KEY (rfp_run_id, supplier_name),
                UNIQUE (rfp_run_id, file_sha256)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_documents_sha256
                ON supplier_documents(file_sha256);
            CREATE TABLE IF NOT EXISTS reviewer_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfp_run_id TEXT NOT NULL REFERENCES rfp_runs(rfp_run_id),
                supplier_name TEXT NOT NULL,
                reviewer_name TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        count = db.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
        if count == 0:
            db.executemany(
                "INSERT INTO evaluation_criteria (name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, 1)",
                DEFAULT_CRITERIA,
            )


def active_criteria(database_path: Path | str) -> list[Criterion]:
    with connect(database_path) as db:
        rows = db.execute(
            "SELECT criterion_id, name, description, weight, max_score, is_active FROM evaluation_criteria WHERE is_active = 1 ORDER BY criterion_id"
        ).fetchall()
    criteria = [Criterion(**dict(row)) for row in rows]
    if not criteria:
        raise ValueError("At least one active criterion is required.")
    total = sum((criterion.weight for criterion in criteria), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"Active criteria weights must total 100; they total {total}.")
    return criteria


def all_criteria(database_path: Path | str) -> list[Criterion]:
    with connect(database_path) as db:
        rows = db.execute(
            "SELECT criterion_id, name, description, weight, max_score, is_active FROM evaluation_criteria ORDER BY criterion_id"
        ).fetchall()
    return [Criterion(**dict(row)) for row in rows]


def replace_criteria(database_path: Path | str, criteria: list[dict[str, object]]) -> None:
    active = [item for item in criteria if bool(item["is_active"])]
    if not active:
        raise ValueError("At least one criterion must be active.")
    total = sum((Decimal(str(item["weight"])) for item in active), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"Active criteria weights must total 100; they total {total}.")
    for item in criteria:
        if not str(item["name"]).strip() or Decimal(str(item["max_score"])) <= 0:
            raise ValueError("Every criterion needs a name and a positive maximum score.")
    with connect(database_path) as db:
        db.execute("DELETE FROM evaluation_criteria")
        db.executemany(
            """INSERT INTO evaluation_criteria
            (criterion_id, name, description, weight, max_score, is_active) VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (int(item["criterion_id"]), str(item["name"]).strip(), str(item["description"]).strip(),
                 float(Decimal(str(item["weight"]))), float(Decimal(str(item["max_score"]))), int(bool(item["is_active"])))
                for item in criteria
            ],
        )


def create_run(database_path: Path | str, criteria: list[Criterion], config: dict[str, object]) -> str:
    run_id = str(uuid4())
    snapshot = [criterion.model_dump(mode="json") for criterion in criteria]
    with connect(database_path) as db:
        db.execute(
            "INSERT INTO rfp_runs (rfp_run_id, created_at, status, criteria_snapshot_json, config_json) VALUES (?, ?, 'running', ?, ?)",
            (run_id, datetime.now(timezone.utc).isoformat(), json.dumps(snapshot, default=_json_default), json.dumps(config)),
        )
    return run_id


def document_sha256(document_bytes: bytes) -> str:
    return hashlib.sha256(document_bytes).hexdigest()


def complete_run(
    database_path: Path | str, run_id: str, suppliers: list[RankedSupplier], inputs: list[SupplierInput]
) -> None:
    """Atomically save every result and its uploaded source document."""
    inputs_by_name = {item.supplier_name.strip().casefold(): item for item in inputs}
    if len(inputs_by_name) != len(inputs) or len(suppliers) != len(inputs):
        raise ValueError("Each saved supplier result must have one uniquely named uploaded PDF.")
    with connect(database_path) as db:
        for supplier in suppliers:
            source = inputs_by_name.get(supplier.supplier_name.casefold())
            if source is None:
                raise ValueError(f"No uploaded PDF was found for {supplier.supplier_name}.")
            result = supplier.model_dump(mode="json")
            db.execute(
                """INSERT INTO supplier_results
                (rfp_run_id, supplier_name, submission_date, experience_rating, absolute_score, ppi, final_rank, result_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, supplier.supplier_name, supplier.submission_date.isoformat(), float(supplier.experience_rating),
                 float(supplier.absolute_score), float(supplier.ppi), supplier.final_rank,
                 json.dumps(result, default=_json_default)),
            )
            db.execute(
                """INSERT INTO supplier_documents
                (rfp_run_id, supplier_name, file_name, file_sha256, document_bytes)
                VALUES (?, ?, ?, ?, ?)""",
                (run_id, supplier.supplier_name, source.document_name, document_sha256(source.document_bytes), source.document_bytes),
            )
        db.execute("UPDATE rfp_runs SET status = 'completed' WHERE rfp_run_id = ?", (run_id,))


def fail_run(database_path: Path | str, run_id: str, message: str) -> None:
    with connect(database_path) as db:
        db.execute("UPDATE rfp_runs SET status = 'failed', error_message = ? WHERE rfp_run_id = ?", (message, run_id))


def load_run(database_path: Path | str, run_id: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    with connect(database_path) as db:
        run = db.execute("SELECT * FROM rfp_runs WHERE rfp_run_id = ?", (run_id,)).fetchone()
        if run is None:
            raise KeyError(f"Unknown run ID: {run_id}")
        rows = db.execute("SELECT result_json FROM supplier_results WHERE rfp_run_id = ? ORDER BY final_rank", (run_id,)).fetchall()
    return dict(run), [json.loads(row["result_json"]) for row in rows]


def list_completed_runs(database_path: Path | str) -> list[dict[str, object]]:
    """Return saved runs with a supplier count for the dashboard selector."""
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT r.rfp_run_id, r.created_at, r.status, COUNT(s.supplier_name) AS supplier_count
               FROM rfp_runs AS r
               LEFT JOIN supplier_results AS s ON s.rfp_run_id = r.rfp_run_id
               WHERE r.status = 'completed'
               GROUP BY r.rfp_run_id, r.created_at, r.status
               ORDER BY r.created_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def find_saved_documents(database_path: Path | str, document_hashes: list[str]) -> list[dict[str, object]]:
    """Find previously saved PDFs by their content hash, regardless of filename."""
    if not document_hashes:
        return []
    placeholders = ", ".join("?" for _ in document_hashes)
    with connect(database_path) as db:
        rows = db.execute(
            f"""SELECT d.file_name, d.file_sha256, d.supplier_name, d.rfp_run_id, r.created_at
                FROM supplier_documents AS d
                JOIN rfp_runs AS r ON r.rfp_run_id = d.rfp_run_id
                WHERE r.status = 'completed' AND d.file_sha256 IN ({placeholders})
                ORDER BY r.created_at DESC""",
            document_hashes,
        ).fetchall()
    return [dict(row) for row in rows]


def list_run_documents(database_path: Path | str, run_id: str) -> list[dict[str, object]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT supplier_name, file_name, file_sha256
               FROM supplier_documents WHERE rfp_run_id = ? ORDER BY supplier_name COLLATE NOCASE""",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def load_document(database_path: Path | str, run_id: str, supplier_name: str) -> dict[str, object] | None:
    with connect(database_path) as db:
        row = db.execute(
            """SELECT file_name, file_sha256, document_bytes FROM supplier_documents
               WHERE rfp_run_id = ? AND supplier_name = ? COLLATE NOCASE""",
            (run_id, supplier_name),
        ).fetchone()
    return dict(row) if row else None


def add_reviewer_note(
    database_path: Path | str, run_id: str, supplier_name: str, reviewer_name: str, recommendation: str, note: str
) -> None:
    if not reviewer_name.strip() or not note.strip():
        raise ValueError("Reviewer name and note are required.")
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO reviewer_notes
            (rfp_run_id, supplier_name, reviewer_name, recommendation, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (run_id, supplier_name, reviewer_name.strip(), recommendation, note.strip(), datetime.now(timezone.utc).isoformat()),
        )


def list_reviewer_notes(database_path: Path | str, run_id: str, supplier_name: str) -> list[dict[str, object]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT reviewer_name, recommendation, note, created_at FROM reviewer_notes
               WHERE rfp_run_id = ? AND supplier_name = ? COLLATE NOCASE ORDER BY created_at DESC""",
            (run_id, supplier_name),
        ).fetchall()
    return [dict(row) for row in rows]
