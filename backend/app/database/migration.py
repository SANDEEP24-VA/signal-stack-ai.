"""Schema compatibility migration helper for SQLite.

Ensures that new columns added to SQLAlchemy models are dynamically added
to existing SQLite database tables without altering or dropping historical data.
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# Table -> list of (column_name, column_sql_type, default_clause)
REQUIRED_COLUMNS = {
    "research_runs": [
        ("pages_skipped_limit", "INTEGER DEFAULT 0", "0"),
        ("pages_skipped_robots", "INTEGER DEFAULT 0", "0"),
        ("pages_skipped_duplicate", "INTEGER DEFAULT 0", "0"),
        ("pages_skipped_out_of_scope", "INTEGER DEFAULT 0", "0"),
    ],
    "company_facts": [
        ("quote_start_offset", "INTEGER", None),
        ("quote_end_offset", "INTEGER", None),
        ("rejection_reason", "TEXT", None),
        ("provenance", "JSON", None),
        ("provenance_type", "VARCHAR(50) DEFAULT 'PUBLIC_VERIFIED_FACT'", "'PUBLIC_VERIFIED_FACT'"),
    ],
    "company_profiles": [
        ("study_destinations", "JSON DEFAULT '[]'", "'[]'"),
        ("business_partners", "JSON DEFAULT '[]'", "'[]'"),
        ("interview_session_id", "INTEGER", None),
    ],
}


def ensure_schema_compatibility(engine: Engine) -> None:
    """Inspect tables and add missing columns using ALTER TABLE if needed."""
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        with engine.connect() as conn:
            for table_name, columns in REQUIRED_COLUMNS.items():
                if table_name not in existing_tables:
                    continue

                existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                for col_name, col_def, default_val in columns:
                    if col_name not in existing_cols:
                        logger.info(f"Adding missing column '{col_name}' to table '{table_name}'")
                        alter_query = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"
                        conn.execute(text(alter_query))
                        conn.commit()
    except Exception as e:
        logger.warning(f"Schema compatibility check warning: {e}")
