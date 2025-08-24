from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
import sqlite3, json, os
import numpy as np
from datetime import datetime
import gunicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(BASE_DIR, "saved_pages")
DB = os.path.join(BASE_DIR, "history.db")
os.makedirs(SAVED, exist_ok=True)

app = Flask(__name__)
CORS(app)

# ---------- DB helpers ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
      CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        operation TEXT NOT NULL,
        matrixA TEXT NOT NULL,
        matrixB TEXT NOT NULL,
        result TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    """)
    conn.commit()
    conn.close()

def save_history(operation, A, B, result):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO history (operation, matrixA, matrixB, result) VALUES (?,?,?,?)",
              (operation, json.dumps(A), json.dumps(B), json.dumps(result)))
    conn.commit()
    nid = c.lastrowid
    c.execute("SELECT created_at FROM history WHERE id=?", (nid,))
    ts = c.fetchone()[0]
    conn.close()
    create_saved_page(nid, operation, A, B, result, ts)
    return nid, ts

def fetch_history(limit=500):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, operation, matrixA, matrixB, result, created_at FROM history ORDER BY id DESC LIMIT ?",
              (limit,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "operation": r[1],
            "A": json.loads(r[2]),
            "B": json.loads(r[3]),
            "result": json.loads(r[4]),
            "time": r[5]
        })
    return out

def delete_entry(eid):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE id=?", (eid,))
    conn.commit()
    conn.close()
    for fn in os.listdir(SAVED):
        if fn.startswith(f"entry_{eid}_"):
            try:
                os.remove(os.path.join(SAVED, fn))
            except Exception:
                pass

def create_saved_page(id_, operation, A, B, result, ts):
    safe_ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d_%H%M%S")
    filename = f"entry_{id_}_{safe_ts}.html"
    path = os.path.join(SAVED, filename)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saved Entry #{id_}</title></head>
    <body style="font-family:system-ui,Arial;padding:24px;background:#081126;color:#eaf4ff">
      <h1>Saved Entry #{id_}</h1>
      <p style="color:#9fb1c9">{operation} — {ts}</p>
      <h3>Matrix A</h3>{render_matrix_html(A)}
      <h3>Matrix B</h3>{render_matrix_html(B)}
      <h3>Result</h3>{render_matrix_html(result)}
      <p><a href="/">Back</a></p>
    </body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def render_matrix_html(mat):
    try:
        html = '<table style="border-collapse:collapse">'
        for row in mat:
            html += "<tr>" + "".join(f'<td style="border:1px solid rgba(0,0,0,0.12);padding:6px">{val}</td>' for val in row) + "</tr>"
        html += "</table>"
        return html
    except Exception:
        return f"<pre>{mat}</pre>"

# ---------- Routes ----------
@app.route("/calculate", methods=["POST"])
def calculate():
    body = request.get_json(force=True)
    # Change dtype to int
    A = np.array(body.get("A", []), dtype=int)
    B = np.array(body.get("B", []), dtype=int)
    op = body.get("operation")

    try:
        if op == "add":
            if A.shape != B.shape:
                return jsonify({"error":"Matrix sizes must match for addition"}), 400
            res = (A + B).tolist()
        elif op == "sub":
            if A.shape != B.shape:
                return jsonify({"error":"Matrix sizes must match for subtraction"}), 400
            res = (A - B).tolist()
        elif op == "mul":
            if A.shape[1] != B.shape[0]:
                return jsonify({"error":"For multiplication: cols(A) must equal rows(B)"}), 400
            res = (A @ B).tolist()
        elif op == "transposeA":
            res = A.T.tolist()
        elif op == "transposeB":
            res = B.T.tolist()
        else:
            return jsonify({"error":"Invalid operation"}), 400
    except Exception as e:
        return jsonify({"error":str(e)}), 400

    nid, ts = save_history(op, A.tolist(), B.tolist(), res)
    return jsonify({"result": res, "id": nid, "time": ts})

@app.route("/history")
def history():
    limit = request.args.get("limit", 5, type=int)
    return jsonify(fetch_history(limit=limit))

@app.route("/delete-entry/<int:entry_id>", methods=["POST"])
def api_delete(entry_id):
    delete_entry(entry_id)
    return jsonify({"ok": True})

@app.route("/export-entry/<int:entry_id>")
def api_export(entry_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, operation, matrixA, matrixB, result, created_at FROM history WHERE id=?", (entry_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        abort(404)
    out = {"id": r[0], "operation": r[1], "A": json.loads(r[2]), "B": json.loads(r[3]), "result": json.loads(r[4]), "time": r[5]}
    return jsonify(out)

@app.route("/saved_pages/<path:fn>")
def serve_saved(fn):
    return send_from_directory(SAVED, fn)

@app.route("/clear-history", methods=["POST"])
def clear_history():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    for f in os.listdir(SAVED):
        try:
            os.remove(os.path.join(SAVED, f))
        except Exception:
            pass
    return jsonify({"ok": True})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)