from flask import Flask, render_template, jsonify, request, g, Response
import sqlite3
import os
import csv

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

def query_dict(query, args=()):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return [dict(row) for row in rows]

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id

# ---------- API endpoints ----------

@app.route("/api/summary")
def api_summary():
    db = get_db()
    total_lenders = query_dict("SELECT COUNT(*) as count FROM lenders")[0]["count"]
    completed_onboarding = query_dict("SELECT COUNT(*) as count FROM lenders WHERE onboarding_status = 'Completed'")[0]["count"]
    total_queries = query_dict("SELECT COUNT(*) as count FROM queries")[0]["count"]
    open_queries = query_dict("SELECT COUNT(*) as count FROM queries WHERE status != 'Closed'")[0]["count"]
    
    col_stats = query_dict("""
        SELECT 
            COALESCE(SUM(total_loans), 0) as total_loans,
            COALESCE(SUM(collected_amount), 0) as collected,
            COALESCE(SUM(pending_amount), 0) as pending
        FROM collections
    """)[0]
    
    total_loans = col_stats["total_loans"]
    collected = col_stats["collected"]
    pending = col_stats["pending"]
    collection_pct = round((collected / total_loans * 100), 2) if total_loans > 0 else 0
    
    return jsonify({
        "total_lenders": total_lenders,
        "completed_onboarding": completed_onboarding,
        "total_queries": total_queries,
        "open_queries": open_queries,
        "total_loans": total_loans,
        "collected": collected,
        "pending": pending,
        "collection_pct": collection_pct
    })

@app.route("/api/lenders", methods=["GET", "POST"])
def api_lenders():
    if request.method == "POST":
        data = request.json or {}
        name = data.get("name")
        onboarding_date = data.get("onboarding_date")
        onboarding_status = data.get("onboarding_status", "In Progress")
        if not name or not onboarding_date:
            return jsonify({"error": "Name and date are required"}), 400
        
        new_id = execute_db(
            "INSERT INTO lenders (name, onboarding_date, onboarding_status) VALUES (?, ?, ?)",
            (name, onboarding_date, onboarding_status)
        )
        # Default collection row
        execute_db(
            "INSERT INTO collections (lender_id, total_loans, collected_amount, pending_amount) VALUES (?, ?, ?, ?)",
            (new_id, 10000, 0, 10000)
        )
        return jsonify({"message": "Lender created successfully in database", "id": new_id}), 201

    data = query_dict("SELECT id, name, onboarding_date, onboarding_status FROM lenders ORDER BY id DESC")
    return jsonify(data)

@app.route("/api/queries", methods=["GET", "POST"])
def api_queries():
    if request.method == "POST":
        data = request.json or {}
        lender_id = data.get("lender_id")
        title = data.get("title")
        priority = data.get("priority", "Medium")
        status = data.get("status", "Open")
        assigned_to = data.get("assigned_to", "Unassigned")
        if not title:
            return jsonify({"error": "Title is required"}), 400
            
        new_id = execute_db(
            "INSERT INTO queries (lender_id, title, priority, status, assigned_to) VALUES (?, ?, ?, ?, ?)",
            (lender_id, title, priority, status, assigned_to)
        )
        return jsonify({"message": "Query ticket created successfully in database", "id": new_id}), 201

    data = query_dict("""
        SELECT q.id, q.lender_id, COALESCE(l.name, 'Unknown') as lender_name, q.title, q.priority, q.status, q.assigned_to 
        FROM queries q 
        LEFT JOIN lenders l ON q.lender_id = l.id
        ORDER BY q.id DESC
    """)
    return jsonify(data)

@app.route("/api/query/<int:query_id>")
def api_query_detail(query_id):
    row = query_dict("""
        SELECT q.id, q.lender_id, COALESCE(l.name, 'Unknown') as lender_name, q.title, q.priority, q.status, q.assigned_to 
        FROM queries q 
        LEFT JOIN lenders l ON q.lender_id = l.id 
        WHERE q.id = ?
    """, (query_id,))
    if row:
        return jsonify(row[0])
    return jsonify({"error": "Not found"}), 404

@app.route("/api/collections")
def api_collections():
    rows = query_dict(
        """
        SELECT l.id as lender_id, l.name as lender_name,
               COALESCE(SUM(c.total_loans), 0) as total_loans,
               COALESCE(SUM(c.collected_amount), 0) as collected_amount,
               COALESCE(SUM(c.pending_amount), 0) as pending_amount
        FROM lenders l
        LEFT JOIN collections c ON l.id = c.lender_id
        GROUP BY l.id
        ORDER BY l.id ASC
        """
    )
    for r in rows:
        total = r["total_loans"] or 0
        collected = r["collected_amount"] or 0
        r["collection_pct"] = round((collected / total) * 100, 2) if total else 0
    return jsonify(rows)

@app.route("/download/queries")
def download_queries():
    rows = query_dict("""
        SELECT q.id, COALESCE(l.name, 'N/A') as lender_name, q.title, q.priority, q.status, q.assigned_to 
        FROM queries q 
        LEFT JOIN lenders l ON q.lender_id = l.id
    """)
    def generate():
        yield "ID,Lender,Title,Priority,Status,Owner\n"
        for r in rows:
            yield f'"{r["id"]}","{r["lender_name"]}","{r["title"]}","{r["priority"]}","{r["status"]}","{r["assigned_to"]}"\n'
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=queries_report.csv"})

# Raw Database check endpoint for user inspection
@app.route("/api/db-inspect")
def api_db_inspect():
    lenders = query_dict("SELECT * FROM lenders")
    queries = query_dict("SELECT * FROM queries")
    collections = query_dict("SELECT * FROM collections")
    return jsonify({
        "database_file": DATABASE,
        "database_exists": os.path.exists(DATABASE),
        "database_size_bytes": os.path.getsize(DATABASE) if os.path.exists(DATABASE) else 0,
        "tables": {
            "lenders": {"count": len(lenders), "rows": lenders},
            "queries": {"count": len(queries), "rows": queries},
            "collections": {"count": len(collections), "rows": collections}
        }
    })

# ---------- UI ----------
@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
