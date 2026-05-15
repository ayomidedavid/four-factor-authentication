from init_db import create_db
from app import app, db


def clear_database():
    create_db()
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("All database tables have been cleared and recreated.")


if __name__ == '__main__':
    clear_database()
