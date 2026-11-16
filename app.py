from flask import Flask, render_template, jsonify, request, g
import sqlite3
import os

app = Flask(__name__)

DATABASE = os.path.join(app.root_path, "lendtrack.db")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()

# ---------- Helper queries ----------

def query_dict(query, args=()):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return [dict(row) for row in rows]

# ---------- API endpoints ----------
@app.route("/api/lenders")
def api_lenders():
    data = query_dict("SELECT id, name, onboarding_date, onboarding_status FROM lenders")
    return jsonify(data)

@app.route("/api/queries")
def api_queries():
    data = query_dict("SELECT id, lender_id, title, priority, status, assigned_to FROM queries")
    return jsonify(data)

@app.route("/api/collections")
def api_collections():
    # Returns aggregated collection metrics per lender
    rows = query_dict(
        """
        SELECT l.id as lender_id, l.name as lender_name,
               SUM(c.total_loans) as total_loans,
               SUM(c.collected_amount) as collected_amount,
               SUM(c.pending_amount) as pending_amount
        FROM lenders l
        LEFT JOIN collections c ON l.id = c.lender_id
        GROUP BY l.id
        """
    )
    # add collection %
    for r in rows:
        total = r["total_loans"] or 0
        collected = r["collected_amount"] or 0
        r["collection_pct"] = round((collected / total) * 100, 2) if total else 0
    return jsonify(rows)

# ---------- UI ----------
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    # Ensure DB exists
    if not os.path.exists(DATABASE):
        print("Database not found. Run init_db.py first.")
    else:
        app.run(debug=True, host="0.0.0.0", port=5001)

