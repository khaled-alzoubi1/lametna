import pytest
from app import db, Team, Event, app
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

def test_db_fk_constraint(test_app):
    with test_app.app_context():
        # Check SQLite PRAGMA for FK
        is_sqlite = 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']
        if is_sqlite:
            result = db.session.execute(text("PRAGMA foreign_key_list(events)")).fetchall()
            # Result format: id, seq, table, from, to, on_update, on_delete, match
            fk_found = False
            for row in result:
                if row.table == 'teams' and row._mapping['from'] == 'team_id' and row._mapping['to'] == 'id':
                    fk_found = True
                    # Check ON DELETE SET NULL
                    assert row.on_delete == 'SET NULL'
            assert fk_found, "Foreign Key to teams not found in events table PRAGMA"
