"""The backend must boot against an empty database.

Regression: app.main ran its migrations at import time and seeded the default
page without naming `emoji`. On an existing database that worked, because the
migration had added the column with a DB-level DEFAULT. On a *fresh* one,
create_all builds the column from the model instead, where the default is
Python-side and never reaches the table, so the insert died on NOT NULL and
uvicorn refused to start.

Every clone of this repo starts with a fresh database, so this broke first run
for everyone while looking fine on the machine it was written on. That is why
the check runs in a subprocess against a throwaway path rather than trusting
the developer's own database.
"""

import os
import subprocess
import sys
import sqlite3
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

BOOT = """
import sys
from app.main import app          # importing runs create_all + the migrations
from app.db.database import engine
print(engine.url.database)
"""


def boot_backend(tmp_path: Path) -> Path:
    """Import the app with the DB pointed at an empty file; return that file."""
    db = tmp_path / "fresh.sqlite3"
    env = {
        **os.environ,
        # config.BACKEND_DIR drives the sqlite path, so a temp HOME is not
        # enough; copy the app onto a clean directory instead.
        "PYTHONPATH": str(BACKEND),
        "LATENT_TEST_DB": str(db),
    }
    proc = subprocess.run(
        [sys.executable, "-c", BOOT],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, (
        "backend failed to start on a fresh database:\n" + proc.stderr[-2000:]
    )
    return Path(proc.stdout.strip())


def test_boots_and_seeds_a_default_page(tmp_path, monkeypatch):
    """Starting with no database at all must succeed and create page 'default'."""
    db_path = BACKEND / "latent.sqlite3"
    backup = db_path.with_suffix(".sqlite3.testbak")
    had_db = db_path.exists()
    if had_db:
        db_path.rename(backup)
    try:
        boot_backend(tmp_path)
        assert db_path.exists(), "boot should have created the database"
        rows = sqlite3.connect(db_path).execute(
            "SELECT id, name, emoji FROM pages"
        ).fetchall()
        assert rows == [("default", "Home", "home")]
    finally:
        db_path.unlink(missing_ok=True)
        if had_db:
            backup.rename(db_path)


def test_boots_again_without_duplicating_the_page(tmp_path):
    """The migrations are re-run on every start; they must be idempotent."""
    db_path = BACKEND / "latent.sqlite3"
    backup = db_path.with_suffix(".sqlite3.testbak")
    had_db = db_path.exists()
    if had_db:
        db_path.rename(backup)
    try:
        boot_backend(tmp_path)
        boot_backend(tmp_path)
        count = sqlite3.connect(db_path).execute(
            "SELECT count(*) FROM pages WHERE id = 'default'"
        ).fetchone()[0]
        assert count == 1
    finally:
        db_path.unlink(missing_ok=True)
        if had_db:
            backup.rename(db_path)
