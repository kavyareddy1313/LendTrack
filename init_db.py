import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "lendtrack.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS lenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            onboarding_date TEXT,
            onboarding_status TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lender_id INTEGER,
            title TEXT,
            priority TEXT,
            status TEXT,
            assigned_to TEXT,
            FOREIGN KEY(lender_id) REFERENCES lenders(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lender_id INTEGER,
            total_loans REAL,
            collected_amount REAL,
            pending_amount REAL,
            FOREIGN KEY(lender_id) REFERENCES lenders(id)
        )
    ''')
    # Insert sample data
    lenders = [
        ("ABC Finance", "2023-01-10", "Completed"),
        ("XYZ Lending", "2023-02-05", "In Progress"),
        ("MoneyMates", "2023-03-12", "Completed")
    ]
    c.executemany('INSERT INTO lenders (name, onboarding_date, onboarding_status) VALUES (?,?,?)', lenders)

    queries = [
        (1, "Login issues", "High", "Open", "Alice"),
        (2, "Report not loading", "Medium", "In Progress", "Bob"),
        (1, "Data sync error", "Low", "Closed", "Charlie")
    ]
    c.executemany('INSERT INTO queries (lender_id, title, priority, status, assigned_to) VALUES (?,?,?,?,?)', queries)

    collections = [
        (1, 5000, 3500, 1500),
        (2, 8000, 5600, 2400),
        (3, 3000, 2100, 900)
    ]
    c.executemany('INSERT INTO collections (lender_id, total_loans, collected_amount, pending_amount) VALUES (?,?,?,?)', collections)

    conn.commit()
    conn.close()
    print("Database initialized with sample data.")

if __name__ == "__main__":
    init_db()

