from sqlalchemy.orm import Session
from app.db.database import engine, Base
import sys, os

def init_db(db: Session):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database table creation notice: {e}")

    # Safe SQLite column migration helper
    try:
        with engine.connect() as conn:
            # Check question_papers columns
            qp_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(question_papers)").fetchall()]
            new_qp_cols = [
                ("examination_id", "INTEGER"),
                ("selected_units_json", "JSON"),
                ("raw_text", "TEXT"),
                ("normalized_text", "TEXT"),
                ("instructions_json", "JSON")
            ]
            for col_name, col_type in new_qp_cols:
                if col_name not in qp_cols:
                    try:
                        conn.exec_driver_sql(f"ALTER TABLE question_papers ADD COLUMN {col_name} {col_type}")
                    except Exception as e:
                        print(f"Migration note (question_papers.{col_name}): {e}")

            # Synchronize QuestionPaper.overall_score with latest ScrutinyReport.overall_score if null
            try:
                conn.exec_driver_sql("""
                    UPDATE question_papers
                    SET overall_score = (
                        SELECT sr.overall_score 
                        FROM scrutiny_reports sr 
                        WHERE sr.paper_id = question_papers.id 
                        ORDER BY sr.version DESC 
                        LIMIT 1
                    )
                    WHERE (question_papers.overall_score IS NULL OR question_papers.overall_score = 0)
                    AND EXISTS (
                        SELECT 1 FROM scrutiny_reports sr2 WHERE sr2.paper_id = question_papers.id AND sr2.overall_score IS NOT NULL
                    )
                """)
            except Exception as e:
                print(f"Sync score note: {e}")

            # Check extracted_questions columns
            eq_cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(extracted_questions)").fetchall()]
            new_eq_cols = [
                ("question_type", "VARCHAR(50) DEFAULT 'QUESTION'"),
                ("parent_question_id", "INTEGER"),
                ("choice_group_id", "VARCHAR(100)"),
                ("parse_confidence", "FLOAT DEFAULT 1.0"),
                ("marks_confidence", "FLOAT"),
                ("metadata_confidence", "FLOAT"),
                ("co_code", "VARCHAR(20)"),
                ("bloom_level", "VARCHAR(50)"),
                ("topic_name", "VARCHAR(255)"),
                ("raw_text", "TEXT"),
                ("normalized_text", "TEXT"),
                ("is_unit_selected", "BOOLEAN DEFAULT 1"),
                ("unit_validation_status", "VARCHAR(50) DEFAULT 'VALID'")
            ]
            for col_name, col_type in new_eq_cols:
                if col_name not in eq_cols:
                    try:
                        conn.exec_driver_sql(f"ALTER TABLE extracted_questions ADD COLUMN {col_name} {col_type}")
                    except Exception as e:
                        print(f"Migration note (extracted_questions.{col_name}): {e}")
            conn.commit()
    except Exception as e:
        print(f"Notice during safe schema migration: {e}")

    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        scripts_dir = os.path.join(root_dir, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import seed_data
        seed_data.seed()
    except Exception as e:
        print(f"Notice during startup seeding: {e}")
