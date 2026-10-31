from pathlib import Path

from src.database import initialize_database


if __name__ == "__main__":
    initialize_database(Path("rfp_evaluation.sqlite3"))
    print("Database initialized and default criteria seeded.")
