
from sqlalchemy import inspect, text

from database import engine


def migrate_database():
    inspector = inspect(engine)

    if "founders" not in inspector.get_table_names():
        print("The founders table does not exist yet.")
        print("Start the application first, then run this script.")
        return

    columns = {
        column["name"]
        for column in inspector.get_columns("founders")
    }

    with engine.begin() as connection:
        if "outreach_status" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE founders "
                    "ADD COLUMN outreach_status VARCHAR(50) "
                    "NOT NULL DEFAULT 'not_contacted'"
                )
            )
            print("Added outreach_status column.")

        if "outreach_draft" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE founders "
                    "ADD COLUMN outreach_draft TEXT"
                )
            )
            print("Added outreach_draft column.")

    print("Database migration complete.")


if __name__ == "__main__":
    migrate_database()
