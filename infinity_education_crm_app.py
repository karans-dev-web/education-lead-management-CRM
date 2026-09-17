"""
Infinity Education — Lead & Counselling CRM
Single-file Flask + SQLite application.

SETUP
-----
1. Install Flask:  python -m pip install Flask
2. Run:  python infinity_education_crm_app.py
3. Open: http://localhost:5000

On first run this file creates all tables and seeds sample courses, counsellors and
a few demo leads automatically — no separate schema.sql needed.
"""

import os
import sqlite3
from flask import Flask, request, jsonify, Response

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------

DB_FILE = os.environ.get(
  "DB_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "infinity_education.db")
)

STATUSES = ["New", "Contacted", "Interested", "Follow-up", "Converted", "Not Interested"]
SOURCES = ["Instagram", "Google", "Referral", "Website"]

app = Flask(__name__)


def get_conn():
  conn = sqlite3.connect(DB_FILE)
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA foreign_keys = ON")
  return conn


# ------------------------------------------------------------------
# Database bootstrap: create DB, tables, seed data — all in this file
# ------------------------------------------------------------------

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS counsellors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            active INTEGER NOT NULL DEFAULT 1
          )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
          )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            city TEXT,
            course_id INT,
            source TEXT NOT NULL DEFAULT 'Website',
            status TEXT NOT NULL DEFAULT 'New',
            counsellor_id INT,
            followup_date TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL,
            FOREIGN KEY (counsellor_id) REFERENCES counsellors(id) ON DELETE SET NULL,
            CHECK (source IN ('Instagram','Google','Referral','Website')),
            CHECK (status IN ('New','Contacted','Interested','Follow-up','Converted','Not Interested'))
          )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS lead_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
          )
    """)

    conn.commit()

    # 3. Seed reference data + demo leads, only if empty
    cur.execute("SELECT COUNT(*) FROM counsellors")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO counsellors (name, email) VALUES (?, ?)",
            [
                ("Priya Sharma", "priya@infinityeducation.in"),
                ("Rahul Verma", "rahul@infinityeducation.in"),
                ("Ananya Singh", "ananya@infinityeducation.in"),
                ("Karan Mehta", "karan@infinityeducation.in"),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM courses")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO courses (name) VALUES (?)",
            [
                ("Data Science & AI",),
                ("Full Stack Web Development",),
                ("Digital Marketing",),
                ("UI/UX Design",),
                ("Business Analytics",),
                ("Cloud Computing (AWS/Azure)",),
                ("Spoken English",),
                ("IELTS/PTE Preparation",),
            ],
        )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM leads")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO leads (name, phone, email, city, course_id, source, status,
                                   counsellor_id, followup_date)
               VALUES
               ('Ayaan Khan','9876543210','ayaan.khan@gmail.com','Lucknow',1,'Instagram','Follow-up',1, date('now','+1 day')),
               ('Simran Kaur','9123456780','simran.k@gmail.com','Chandigarh',4,'Google','Interested',2, date('now','-2 day')),
               ('Rohan Mehta','9000011223',NULL,'Indore',2,'Referral','Converted',4, NULL),
               ('Neha Yadav','8899012345','neha.yadav@gmail.com','Kanpur',3,'Website','New',3, NULL),
               ('Vikram Rathore','9988776655','vikram.r@gmail.com','Jaipur',6,'Instagram','Contacted',1, date('now'))
            """
        )
        conn.commit()

    cur.close()
    conn.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

LEAD_SELECT = """
    SELECT l.*, c.name AS course_name, u.name AS counsellor_name
    FROM leads l
    LEFT JOIN courses c ON c.id = l.course_id
    LEFT JOIN counsellors u ON u.id = l.counsellor_id
"""


def row_to_lead(row):
  def as_text(value):
    return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row["email"],
        "city": row["city"],
        "course_id": row["course_id"],
        "course": row["course_name"],
        "source": row["source"],
        "status": row["status"],
        "counsellor_id": row["counsellor_id"],
        "counsellor": row["counsellor_name"],
        "followup_date": as_text(row["followup_date"]),
        "created_at": as_text(row["created_at"]),
    }


# ------------------------------------------------------------------
# API routes
# ------------------------------------------------------------------

@app.route("/api/meta")
def api_meta():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM courses WHERE active = 1 ORDER BY name")
    courses = [dict(row) for row in cur.fetchall()]
    cur.execute("SELECT id, name FROM counsellors WHERE active = 1 ORDER BY name")
    counsellors = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify({"courses": courses, "counsellors": counsellors,
                     "statuses": STATUSES, "sources": SOURCES})


@app.route("/api/leads", methods=["GET"])
def api_list_leads():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    source = request.args.get("source", "").strip()
    course_id = request.args.get("course_id", "").strip()
    counsellor_id = request.args.get("counsellor_id", "").strip()

    where, params = [], []
    if q:
        like = f"%{q}%"
        where.append("(l.name LIKE ? OR l.phone LIKE ? OR l.email LIKE ? OR l.city LIKE ?)")
        params += [like, like, like, like]
    if status:
        where.append("l.status = ?"); params.append(status)
    if source:
        where.append("l.source = ?"); params.append(source)
    if course_id:
        where.append("l.course_id = ?"); params.append(course_id)
    if counsellor_id:
        where.append("l.counsellor_id = ?"); params.append(counsellor_id)

    sql = LEAD_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY l.created_at DESC"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row_to_lead(r) for r in rows])


@app.route("/api/leads", methods=["POST"])
def api_create_lead():
    data = request.get_json(force=True)
    required = ["name", "phone", "city", "course_id", "source", "counsellor_id"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    if data["source"] not in SOURCES:
        return jsonify({"error": "Invalid lead source"}), 400

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO leads (name, phone, email, city, course_id, source, status,
                               counsellor_id, followup_date)
           VALUES (?,?,?,?,?,?, 'New',?,?)""",
        (data["name"], data["phone"], data.get("email"), data["city"],
         data["course_id"], data["source"], data["counsellor_id"],
         data.get("followup_date") or None),
    )
    lead_id = cur.lastrowid
    note = (data.get("note") or "").strip()
    if note:
        cur.execute("INSERT INTO lead_notes (lead_id, note) VALUES (?, ?)", (lead_id, note))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": lead_id}), 201


@app.route("/api/leads/<int:lead_id>", methods=["PUT"])
def api_update_lead(lead_id):
    data = request.get_json(force=True)
    fields, params = [], []
    if "status" in data:
        if data["status"] not in STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        fields.append("status = ?"); params.append(data["status"])
    if "counsellor_id" in data:
        fields.append("counsellor_id = ?"); params.append(data["counsellor_id"])
    if "followup_date" in data:
        fields.append("followup_date = ?"); params.append(data["followup_date"] or None)
    if not fields:
        return jsonify({"error": "Nothing to update"}), 400

    params.append(lead_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"UPDATE leads SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def api_delete_lead(lead_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/leads/<int:lead_id>/notes", methods=["GET"])
def api_get_notes(lead_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, note, created_at FROM lead_notes WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
      {"id": r["id"], "note": r["note"], "created_at": r["created_at"]}
      for r in rows
    ])


@app.route("/api/leads/<int:lead_id>/notes", methods=["POST"])
def api_add_note(lead_id):
    data = request.get_json(force=True)
    note = (data.get("note") or "").strip()
    if not note:
        return jsonify({"error": "Note text is required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO lead_notes (lead_id, note) VALUES (?, ?)", (lead_id, note))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True}), 201


@app.route("/api/dashboard")
def api_dashboard():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status, COUNT(*) AS n FROM leads GROUP BY status")
    by_status = {r["status"]: r["n"] for r in cur.fetchall()}

    cur.execute("SELECT source, COUNT(*) AS n FROM leads GROUP BY source")
    by_source = {r["source"]: r["n"] for r in cur.fetchall()}

    cur.execute("""
        SELECT u.name AS counsellor,
               COUNT(*) AS assigned,
               SUM(CASE WHEN l.status = 'Converted' THEN 1 ELSE 0 END) AS converted
        FROM leads l JOIN counsellors u ON u.id = l.counsellor_id
        GROUP BY u.name
    """)
    by_counsellor = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT COUNT(*) AS n FROM leads")
    total = cur.fetchone()["n"]
    cur.close()
    conn.close()

    converted = by_status.get("Converted", 0)
    rate = round((converted / total) * 100, 1) if total else 0
    for s in STATUSES:
        by_status.setdefault(s, 0)
    for s in SOURCES:
        by_source.setdefault(s, 0)

    return jsonify({
        "total": total,
        "converted": converted,
        "interested": by_status.get("Interested", 0),
        "pending_followup": by_status.get("Follow-up", 0),
        "conversion_rate": rate,
        "by_status": by_status,
        "by_source": by_source,
        "by_counsellor": by_counsellor,
    })


# ------------------------------------------------------------------
# Frontend (single page, served straight from this file)
# ------------------------------------------------------------------

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Infinity Education — Lead & Counselling CRM</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#F6F4EE; --surface:#FFFFFF; --surface-2:#EFEBE0; --ink:#1B2A4A; --ink-soft:#3E4A63;
    --muted:#6B7280; --border:#E1DCCE; --gold:#B4842A; --gold-soft:#F1E6CD; --sage:#2F6B4F;
    --sage-soft:#DEEAE2; --amber:#A6631B; --amber-soft:#F2E2CE; --brick:#B0473A; --brick-soft:#F6E1DE;
    --slate:#5B6B8C; --slate-soft:#E4E8F0; --shadow:0 1px 2px rgba(27,42,74,0.06), 0 6px 20px rgba(27,42,74,0.06);
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --bg:#10141C; --surface:#181E29; --surface-2:#1F2634; --ink:#EDEAE0; --ink-soft:#C7CCD9;
      --muted:#9AA1B0; --border:#2A3140; --gold:#D6A24C; --gold-soft:#3A2E17; --sage:#6FBE96;
      --sage-soft:#1B3327; --amber:#D89452; --amber-soft:#3A2A16; --brick:#E08477; --brick-soft:#3B211E;
      --slate:#96A6CC; --slate-soft:#232A3C; --shadow:0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.35);
    }
  }
  *{box-sizing:border-box;}
  body{ margin:0; background:radial-gradient(circle at 90% -10%, rgba(180,132,42,0.12), transparent 34%), var(--bg); color:var(--ink); font-family:'IBM Plex Sans','Segoe UI',system-ui,sans-serif; -webkit-font-smoothing:antialiased; }
  h1,h2,h3,.brand-name,.stat-num{ font-family:'Fraunces', Georgia, 'Times New Roman', serif; }
  .app{ display:flex; min-height:100vh; }
  .sidebar{ width:250px; flex-shrink:0; background:var(--surface); border-right:1px solid var(--border); display:flex; flex-direction:column; padding:28px 18px; gap:26px; }
  .brand-mark{ font-size:13px; color:var(--gold); margin-bottom:4px; }
  .brand-name{ font-size:23px; font-weight:600; }
  .brand-sub{ font-size:12.5px; color:var(--muted); margin-top:6px; line-height:1.4; }
  nav.primary-nav{ display:flex; flex-direction:column; gap:2px; }
  .nav-btn{ display:flex; align-items:center; gap:10px; text-align:left; background:none; border:none; color:var(--ink-soft); font-size:14.5px; padding:10px 12px; border-radius:9px; cursor:pointer; border-left:3px solid transparent; font-family:inherit; }
  .nav-btn:hover{ background:var(--surface-2); }
  button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible{ outline:3px solid rgba(180,132,42,0.35); outline-offset:2px; }
  .nav-btn.active{ background:var(--gold-soft); color:var(--ink); border-left:3px solid var(--gold); font-weight:600; }
  .nav-dot{ width:7px; height:7px; border-radius:50%; background:currentColor; opacity:0.55; }
  .sidebar-foot{ margin-top:auto; font-size:12px; color:var(--muted); line-height:1.5; }
  .main{ flex:1; min-width:0; padding:34px 42px 60px; }
  .view{ display:none; max-width:1180px; margin:0 auto; }
  .view.active{ display:block; }
  .view-header{ display:flex; align-items:flex-end; justify-content:space-between; gap:20px; margin-bottom:26px; }
  .eyebrow{ color:var(--gold); font-size:11px; font-weight:700; letter-spacing:0.12em; text-transform:uppercase; margin-bottom:8px; }
  .header-meta{ display:flex; align-items:center; gap:8px; color:var(--muted); font-size:12.5px; white-space:nowrap; }
  .live-dot{ width:8px; height:8px; border-radius:50%; background:var(--sage); box-shadow:0 0 0 4px var(--sage-soft); }
  .view-header h1{ font-size:28px; font-weight:600; margin:0 0 6px; }
  .view-header p{ margin:0; color:var(--muted); font-size:14.5px; max-width:640px; line-height:1.5; }
  .stat-grid{ display:grid; grid-template-columns:repeat(5,1fr); gap:14px; margin-bottom:28px; }
  .stat-card{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:18px 18px 16px; box-shadow:var(--shadow); }
  .stat-num{ font-size:30px; font-weight:600; line-height:1; }
  .stat-label{ font-size:12.8px; color:var(--muted); margin-top:8px; }
  .stat-card.accent-gold .stat-num{ color:var(--gold); }
  .stat-card.accent-sage .stat-num{ color:var(--sage); }
  .stat-card.accent-amber .stat-num{ color:var(--amber); }
  .stat-card.accent-brick .stat-num{ color:var(--brick); }
  .chart-grid{ display:grid; grid-template-columns:1.1fr 1fr; gap:16px; margin-bottom:10px; }
  .panel{ background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:20px 22px; box-shadow:var(--shadow); }
  .panel h3{ margin:0 0 4px; font-size:16px; font-weight:600; }
  .panel .panel-sub{ font-size:12.5px; color:var(--muted); margin-bottom:14px; }
  .chart-wrap{ position:relative; height:230px; }
  .chart-wrap.tall{ height:270px; }
  .filters{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:16px; align-items:center; }
  .filters input[type="text"], .filters select{ background:var(--surface); border:1px solid var(--border); color:var(--ink); padding:9px 12px; border-radius:9px; font-size:13.5px; font-family:inherit; }
  .filters input[type="text"]{ min-width:220px; flex:1; }
  .btn{ background:var(--ink); color:var(--bg); border:none; padding:10px 16px; border-radius:9px; font-size:13.8px; font-weight:600; cursor:pointer; font-family:inherit; }
  .btn:hover{ opacity:0.9; }
  .btn.secondary{ background:transparent; color:var(--ink); border:1px solid var(--border); }
  .btn.small{ padding:6px 11px; font-size:12.8px; border-radius:7px; }
  .btn.danger-text{ background:none; border:none; color:var(--brick); text-decoration:underline; cursor:pointer; padding:4px; font-size:13px; }
  .table-scroll{ overflow-x:auto; border:1px solid var(--border); border-radius:14px; background:var(--surface); box-shadow:var(--shadow); }
  table{ width:100%; border-collapse:collapse; font-size:13.6px; min-width:920px; }
  thead th{ text-align:left; padding:13px 16px; color:var(--muted); font-weight:600; font-size:12.3px; border-bottom:1px solid var(--border); white-space:nowrap; }
  tbody td{ padding:13px 16px; border-bottom:1px solid var(--border); vertical-align:middle; }
  tbody tr:last-child td{ border-bottom:none; }
  tbody tr{ cursor:pointer; }
  tbody tr:hover{ background:var(--surface-2); }
  .cell-name{ font-weight:600; }
  .cell-sub{ color:var(--muted); font-size:12.3px; margin-top:2px; }
  .badge{ display:inline-block; padding:4px 10px; border-radius:100px; font-size:12px; font-weight:600; }
  .empty-row td{ text-align:center; color:var(--muted); padding:40px 16px; cursor:default; }
  .empty-row:hover{ background:none; }
  .loading-row td, .error-row td{ text-align:center; color:var(--muted); padding:36px 16px; }
  .error-row td{ color:var(--brick); }
  .form-card{ background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:30px 32px; box-shadow:var(--shadow); max-width:720px; }
  .form-grid{ display:grid; grid-template-columns:1fr 1fr; gap:18px 20px; }
  .field{ display:flex; flex-direction:column; gap:6px; }
  .field.full{ grid-column:1 / -1; }
  .field label{ font-size:13px; font-weight:600; color:var(--ink-soft); }
  .field input, .field select, .field textarea{ background:var(--bg); border:1px solid var(--border); color:var(--ink); padding:10px 12px; border-radius:9px; font-size:14px; font-family:inherit; }
  .field textarea{ resize:vertical; min-height:70px; }
  .form-actions{ margin-top:24px; display:flex; gap:10px; align-items:center; }
  .form-note{ font-size:12.5px; color:var(--muted); margin-top:18px; line-height:1.5; }
  .toast{ position:fixed; bottom:26px; left:50%; transform:translateX(-50%) translateY(20px); opacity:0; background:var(--ink); color:var(--bg); padding:12px 20px; border-radius:10px; font-size:13.8px; box-shadow:var(--shadow); transition:opacity .25s ease, transform .25s ease; pointer-events:none; z-index:80; }
  .toast.show{ opacity:1; transform:translateX(-50%) translateY(0); }
  .fu-group{ margin-bottom:22px; }
  .fu-group-title{ font-size:13px; font-weight:700; margin-bottom:10px; display:flex; align-items:center; gap:8px; }
  .fu-group-title .count{ background:var(--surface-2); color:var(--muted); border-radius:100px; padding:2px 9px; font-size:11.5px; font-weight:600; }
  .fu-card{ background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--slate); border-radius:11px; padding:14px 16px; margin-bottom:9px; cursor:pointer; box-shadow:var(--shadow); display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; }
  .fu-card:hover{ background:var(--surface-2); }
  .fu-card.overdue{ border-left-color:var(--brick); }
  .fu-card.today{ border-left-color:var(--amber); }
  .fu-card.upcoming{ border-left-color:var(--sage); }
  .fu-main .name{ font-weight:600; font-size:14.5px; }
  .fu-main .meta{ font-size:12.5px; color:var(--muted); margin-top:3px; }
  .fu-date{ font-size:12.8px; font-weight:600; padding:5px 11px; border-radius:100px; }
  .fu-date.overdue{ color:var(--brick); background:var(--brick-soft); }
  .fu-date.today{ color:var(--amber); background:var(--amber-soft); }
  .fu-date.upcoming{ color:var(--sage); background:var(--sage-soft); }
  .overlay{ position:fixed; inset:0; background:rgba(16,20,28,0.4); opacity:0; pointer-events:none; transition:opacity .2s ease; z-index:60; }
  .overlay.show{ opacity:1; pointer-events:auto; }
  .drawer{ position:fixed; top:0; right:0; height:100%; width:420px; max-width:92vw; background:var(--surface); border-left:1px solid var(--border); transform:translateX(100%); transition:transform .25s ease; z-index:70; display:flex; flex-direction:column; box-shadow:-8px 0 30px rgba(0,0,0,0.15); }
  .drawer.show{ transform:translateX(0); }
  .drawer-head{ padding:24px 24px 16px; border-bottom:1px solid var(--border); }
  .drawer-head .close-x{ float:right; background:none; border:none; font-size:20px; color:var(--muted); cursor:pointer; line-height:1; }
  .drawer-head h2{ margin:0 0 4px; font-size:20px; font-weight:600; }
  .drawer-head .sub{ color:var(--muted); font-size:13px; }
  .drawer-body{ padding:20px 24px; overflow-y:auto; flex:1; }
  .drawer-section{ margin-bottom:22px; }
  .drawer-section h4{ margin:0 0 10px; font-size:12.5px; color:var(--muted); font-weight:700; }
  .info-line{ display:flex; justify-content:space-between; font-size:13.8px; padding:6px 0; border-bottom:1px dashed var(--border); }
  .info-line span:first-child{ color:var(--muted); }
  .note-item{ background:var(--surface-2); border-radius:9px; padding:10px 12px; margin-bottom:8px; font-size:13px; }
  .note-item .note-date{ font-size:11.3px; color:var(--muted); margin-bottom:3px; font-weight:600; }
  .status-pill-row{ display:flex; flex-wrap:wrap; gap:7px; }
  .status-pill{ border:1px solid var(--border); background:var(--bg); padding:6px 12px; border-radius:100px; font-size:12.6px; cursor:pointer; font-weight:600; color:var(--ink-soft); font-family:inherit; }
  .status-pill.selected{ border-color:transparent; color:#fff; }
  .drawer-select, .drawer-date, .drawer-textarea{ width:100%; padding:9px 12px; border-radius:9px; border:1px solid var(--border); background:var(--bg); color:var(--ink); font-family:inherit; font-size:13.8px; }
  .drawer-textarea{ min-height:64px; resize:vertical; }
  .drawer[aria-hidden="true"]{ visibility:hidden; }
  @media (max-width: 860px){
    .app{ flex-direction:column; }
    .sidebar{ width:100%; flex-direction:row; align-items:center; overflow-x:auto; padding:14px 16px; gap:16px; }
    nav.primary-nav{ flex-direction:row; }
    .sidebar-foot{ display:none; }
    .main{ padding:22px 18px 50px; }
    .stat-grid{ grid-template-columns:repeat(2,1fr); }
    .chart-grid{ grid-template-columns:1fr; }
    .form-grid{ grid-template-columns:1fr; }
    .drawer{ width:100%; max-width:100%; }
    .view-header{ align-items:flex-start; flex-direction:column; gap:12px; }
    .header-meta{ white-space:normal; }
  }
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">Infinity Education</div>
      <div class="brand-name">Lead Desk</div>
      <div class="brand-sub">Enquiry to admission, tracked in one place for the counselling team.</div>
    </div>
    <nav class="primary-nav" id="primaryNav">
      <button class="nav-btn active" data-view="dashboard"><span class="nav-dot"></span>Dashboard</button>
      <button class="nav-btn" data-view="leads"><span class="nav-dot"></span>All leads</button>
      <button class="nav-btn" data-view="new"><span class="nav-dot"></span>New enquiry</button>
      <button class="nav-btn" data-view="followups"><span class="nav-dot"></span>Follow-ups</button>
    </nav>
    <div class="sidebar-foot">Backed by a local database — visible to every counsellor using this app.</div>
  </aside>

  <main class="main">
    <section class="view active" id="view-dashboard">
      <div class="view-header"><div><div class="eyebrow">Operations overview</div><h1>Conversion dashboard</h1><p>Where today's pipeline stands, from first enquiry through to admission.</p></div><div class="header-meta"><span class="live-dot"></span><span>Live pipeline</span><span aria-hidden="true">·</span><span id="todayLabel"></span></div></div>
      <div class="stat-grid" id="statGrid"></div>
      <div class="chart-grid">
        <div class="panel"><h3>Leads by stage</h3><div class="panel-sub">Every lead currently sitting in each part of the pipeline.</div><div class="chart-wrap"><canvas id="chartStatus"></canvas></div></div>
        <div class="panel"><h3>Leads by source</h3><div class="panel-sub">Where enquiries are coming from this period.</div><div class="chart-wrap"><canvas id="chartSource"></canvas></div></div>
      </div>
      <div class="panel" style="margin-top:16px;"><h3>Counsellor performance</h3><div class="panel-sub">Assigned leads vs. admissions confirmed, by counsellor.</div><div class="chart-wrap tall"><canvas id="chartCounsellor"></canvas></div></div>
    </section>

    <section class="view" id="view-leads">
      <div class="view-header"><div><div class="eyebrow">Pipeline workspace</div><h1>All leads</h1><p>Search, filter, and open any enquiry to update its stage or log a call.</p></div></div>
      <div class="filters">
        <input type="text" id="fSearch" placeholder="Search name, phone, email or city">
        <select id="fStatus"><option value="">All stages</option></select>
        <select id="fSource"><option value="">All sources</option></select>
        <select id="fCourse"><option value="">All courses</option></select>
        <select id="fCounsellor"><option value="">All counsellors</option></select>
        <button class="btn secondary small" id="clearFilters">Clear</button>
        <button class="btn small" id="goNewFromLeads" style="margin-left:auto;">+ New enquiry</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Student</th><th>City</th><th>Course</th><th>Source</th><th>Counsellor</th><th>Stage</th><th>Follow-up</th></tr></thead>
          <tbody id="leadsTbody"></tbody>
        </table>
      </div>
    </section>

    <section class="view" id="view-new">
      <div class="view-header"><div><div class="eyebrow">Capture a new opportunity</div><h1>New enquiry</h1><p>Log a student's details the moment they reach out, so nothing is followed up from memory.</p></div></div>
      <form class="form-card" id="enquiryForm">
        <div class="form-grid">
          <div class="field"><label for="inName">Student name</label><input type="text" id="inName" required placeholder="e.g. Ayaan Khan"></div>
          <div class="field"><label for="inPhone">Phone number</label><input type="tel" id="inPhone" required placeholder="e.g. 98765 43210"></div>
          <div class="field"><label for="inEmail">Email</label><input type="email" id="inEmail" placeholder="e.g. ayaan@email.com"></div>
          <div class="field"><label for="inCity">City</label><input type="text" id="inCity" required placeholder="e.g. Lucknow"></div>
          <div class="field"><label for="inCourse">Interested course</label><select id="inCourse" required></select></div>
          <div class="field"><label for="inSource">Lead source</label>
            <select id="inSource" required>
              <option value="Instagram">Instagram</option><option value="Google">Google</option>
              <option value="Referral">Referral</option><option value="Website">Website</option>
            </select>
          </div>
          <div class="field"><label for="inCounsellor">Assign counsellor / BDE</label><select id="inCounsellor" required></select></div>
          <div class="field"><label for="inFollowup">First follow-up date</label><input type="date" id="inFollowup"></div>
          <div class="field full"><label for="inNotes">Enquiry notes</label><textarea id="inNotes" placeholder="What did the student ask about? Any specifics worth remembering."></textarea></div>
        </div>
        <div class="form-actions">
          <button type="submit" class="btn">Save enquiry</button>
          <button type="button" class="btn secondary" id="resetForm">Clear form</button>
        </div>
        <div class="form-note">New enquiries are created with the stage "New". Move them through the pipeline from the lead's detail panel.</div>
      </form>
    </section>

    <section class="view" id="view-followups">
      <div class="view-header"><div><div class="eyebrow">Next actions</div><h1>Follow-ups</h1><p>Every lead with a scheduled follow-up, grouped by urgency so nothing slips.</p></div></div>
      <div id="followupsContainer"></div>
    </section>
  </main>
</div>

<div class="overlay" id="overlay"></div>
<aside class="drawer" id="drawer" aria-hidden="true" aria-label="Lead details">
  <div class="drawer-head">
    <button class="close-x" id="closeDrawer" type="button" aria-label="Close lead details">&times;</button>
    <h2 id="drawerName">Student name</h2>
    <div class="sub" id="drawerCourse">Course</div>
  </div>
  <div class="drawer-body">
    <div class="drawer-section">
      <h4>Contact</h4>
      <div class="info-line"><span>Phone</span><span id="drawerPhone"></span></div>
      <div class="info-line"><span>Email</span><span id="drawerEmail"></span></div>
      <div class="info-line"><span>City</span><span id="drawerCity"></span></div>
      <div class="info-line"><span>Source</span><span id="drawerSource"></span></div>
      <div class="info-line"><span>Created</span><span id="drawerCreated"></span></div>
    </div>
    <div class="drawer-section"><h4>Pipeline stage</h4><div class="status-pill-row" id="statusPillRow"></div></div>
    <div class="drawer-section"><h4>Counsellor / BDE</h4><select id="drawerCounsellor" class="drawer-select"></select></div>
    <div class="drawer-section"><h4>Follow-up date</h4><input type="date" id="drawerFollowup" class="drawer-date"></div>
    <div class="drawer-section">
      <h4>Add a note</h4>
      <textarea id="drawerNoteInput" class="drawer-textarea" placeholder="Call summary, objection raised, next step..."></textarea>
      <button class="btn small" id="addNoteBtn" style="margin-top:8px;">Add note</button>
    </div>
    <div class="drawer-section"><h4>Counselling history</h4><div id="notesList"></div></div>
    <button class="btn danger-text" id="removeLeadBtn">Remove this lead</button>
  </div>
</aside>
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
(function(){
  "use strict";
  var STATUS_COLOR = { "New":"var(--slate)", "Contacted":"var(--gold)", "Interested":"var(--sage)", "Follow-up":"var(--amber)", "Converted":"var(--sage)", "Not Interested":"var(--brick)" };
  var STATUS_SOFT  = { "New":"var(--slate-soft)", "Contacted":"var(--gold-soft)", "Interested":"var(--sage-soft)", "Follow-up":"var(--amber-soft)", "Converted":"var(--sage-soft)", "Not Interested":"var(--brick-soft)" };
  var STATUS_HEX   = { "New":"#5B6B8C", "Contacted":"#B4842A", "Interested":"#2F6B4F", "Follow-up":"#A6631B", "Converted":"#1F5138", "Not Interested":"#B0473A" };
  var SOURCE_HEX   = { "Instagram":"#C2578A", "Google":"#4F7FBF", "Referral":"#B4842A", "Website":"#2F6B4F" };

  var meta = { courses:[], counsellors:[], statuses:[], sources:[] };
  var allLeads = [];
  var activeLeadId = null;
  var charts = {};

  function fmtDate(d){ if(!d) return "—"; var dt=new Date(d+"T00:00:00"); if(isNaN(dt)) return d; return dt.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}); }
  function todayStr(){ var t=new Date(); return t.getFullYear()+"-"+String(t.getMonth()+1).padStart(2,'0')+"-"+String(t.getDate()).padStart(2,'0'); }
  function setTodayLabel(){ document.getElementById("todayLabel").textContent = new Date().toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}); }
  function escapeHtml(s){ if(!s) return ""; return String(s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function showToast(msg){ var t=document.getElementById("toast"); t.textContent=msg; t.classList.add("show"); clearTimeout(showToast._t); showToast._t=setTimeout(function(){ t.classList.remove("show"); },2200); }

  async function api(path, opts){
    opts = opts || {};
    opts.headers = Object.assign({ "Content-Type":"application/json" }, opts.headers || {});
    var res = await fetch(path, opts);
    if(!res.ok){ var body = await res.json().catch(function(){return {};}); throw new Error(body.error || res.statusText); }
    if(res.status === 204) return null;
    return res.json();
  }

  function populateSelect(el, items, valueKey, labelKey, withEmpty, emptyLabel){
    el.innerHTML = "";
    if(withEmpty){ var o=document.createElement("option"); o.value=""; o.textContent=emptyLabel||"—"; el.appendChild(o); }
    items.forEach(function(it){
      var o = document.createElement("option");
      if(typeof it === "string"){ o.value = it; o.textContent = it; }
      else { o.value = it[valueKey]; o.textContent = it[labelKey]; }
      el.appendChild(o);
    });
  }

  async function loadMeta(){
    meta = await api("/api/meta");
    populateSelect(document.getElementById("inCourse"), meta.courses, "id", "name");
    populateSelect(document.getElementById("inCounsellor"), meta.counsellors, "id", "name");
    populateSelect(document.getElementById("drawerCounsellor"), meta.counsellors, "id", "name");
    populateSelect(document.getElementById("fStatus"), meta.statuses, null, null, true, "All stages");
    populateSelect(document.getElementById("fSource"), meta.sources, null, null, true, "All sources");
    populateSelect(document.getElementById("fCourse"), meta.courses, "id", "name", true, "All courses");
    populateSelect(document.getElementById("fCounsellor"), meta.counsellors, "id", "name", true, "All counsellors");
  }

  function setupNav(){
    var btns = document.querySelectorAll(".nav-btn");
    btns.forEach(function(b){
      b.addEventListener("click", function(){
        btns.forEach(function(x){ x.classList.remove("active"); });
        b.classList.add("active");
        var view = b.getAttribute("data-view");
        document.querySelectorAll(".view").forEach(function(v){ v.classList.remove("active"); });
        document.getElementById("view-"+view).classList.add("active");
        if(view === "dashboard") renderDashboard();
        if(view === "leads") loadAndRenderLeads();
        if(view === "followups") renderFollowups();
      });
    });
    document.getElementById("goNewFromLeads").addEventListener("click", function(){
      document.querySelector('.nav-btn[data-view="new"]').click();
    });
  }

  function setupForm(){
    document.getElementById("enquiryForm").addEventListener("submit", async function(e){
      e.preventDefault();
      var payload = {
        name: document.getElementById("inName").value.trim(),
        phone: document.getElementById("inPhone").value.trim(),
        email: document.getElementById("inEmail").value.trim(),
        city: document.getElementById("inCity").value.trim(),
        course_id: document.getElementById("inCourse").value,
        source: document.getElementById("inSource").value,
        counsellor_id: document.getElementById("inCounsellor").value,
        followup_date: document.getElementById("inFollowup").value,
        note: document.getElementById("inNotes").value.trim()
      };
      try{
        await api("/api/leads", { method:"POST", body: JSON.stringify(payload) });
        document.getElementById("enquiryForm").reset();
        showToast("Enquiry saved for " + payload.name);
        document.querySelector('.nav-btn[data-view="leads"]').click();
      }catch(err){ showToast("Could not save: " + err.message); }
    });
    document.getElementById("resetForm").addEventListener("click", function(){
      document.getElementById("enquiryForm").reset();
    });
  }

  function setupFilters(){
    ["fSearch","fStatus","fSource","fCourse","fCounsellor"].forEach(function(id){
      document.getElementById(id).addEventListener("input", loadAndRenderLeads);
      document.getElementById(id).addEventListener("change", loadAndRenderLeads);
    });
    document.getElementById("clearFilters").addEventListener("click", function(){
      document.getElementById("fSearch").value = "";
      document.getElementById("fStatus").value = "";
      document.getElementById("fSource").value = "";
      document.getElementById("fCourse").value = "";
      document.getElementById("fCounsellor").value = "";
      loadAndRenderLeads();
    });
  }

  function buildQuery(){
    var params = new URLSearchParams();
    var q = document.getElementById("fSearch").value.trim();
    var status = document.getElementById("fStatus").value;
    var source = document.getElementById("fSource").value;
    var course_id = document.getElementById("fCourse").value;
    var counsellor_id = document.getElementById("fCounsellor").value;
    if(q) params.set("q", q);
    if(status) params.set("status", status);
    if(source) params.set("source", source);
    if(course_id) params.set("course_id", course_id);
    if(counsellor_id) params.set("counsellor_id", counsellor_id);
    return params.toString();
  }

  async function loadAndRenderLeads(){
    var tbody = document.getElementById("leadsTbody");
    tbody.innerHTML = '<tr class="loading-row"><td colspan="7">Loading leads...</td></tr>';
    try{
      var qs = buildQuery();
      var rows = await api("/api/leads" + (qs ? "?" + qs : ""));
      tbody.innerHTML = "";
      if(rows.length === 0){
        tbody.innerHTML = '<tr class="empty-row"><td colspan="7">No leads match these filters yet.</td></tr>';
        return;
      }
      rows.forEach(function(l){
        var tr = document.createElement("tr");
        tr.tabIndex = 0;
        tr.innerHTML =
          '<td><div class="cell-name">'+escapeHtml(l.name)+'</div><div class="cell-sub">'+escapeHtml(l.phone)+'</div></td>'+
          '<td>'+escapeHtml(l.city||"")+'</td>'+
          '<td>'+escapeHtml(l.course||"—")+'</td>'+
          '<td>'+escapeHtml(l.source)+'</td>'+
          '<td>'+escapeHtml(l.counsellor||"—")+'</td>'+
          '<td><span class="badge" style="background:'+STATUS_SOFT[l.status]+'; color:'+STATUS_COLOR[l.status]+';">'+l.status+'</span></td>'+
          '<td>'+(l.followup_date ? fmtDate(l.followup_date) : "—")+'</td>';
        tr.addEventListener("click", function(){ openDrawer(l.id); });
        tr.addEventListener("keydown", function(e){ if(e.key === "Enter" || e.key === " "){ e.preventDefault(); openDrawer(l.id); } });
        tbody.appendChild(tr);
      });
    }catch(err){
      tbody.innerHTML = '<tr class="error-row"><td colspan="7">Could not load leads. Check that the server is running.</td></tr>';
      showToast("Could not load leads: " + err.message);
    }
  }

  function statCard(num, label, accentClass){
    return '<div class="stat-card '+accentClass+'"><div class="stat-num">'+num+'</div><div class="stat-label">'+label+'</div></div>';
  }

  async function renderDashboard(){
    var grid = document.getElementById("statGrid");
    try{
    var stats = await api("/api/dashboard");
    grid.innerHTML =
      statCard(stats.total, "Total leads", "") +
      statCard(stats.interested, "Interested", "accent-gold") +
      statCard(stats.pending_followup, "Follow-up pending", "accent-amber") +
      statCard(stats.converted, "Converted / admitted", "accent-sage") +
      statCard(stats.conversion_rate + "%", "Conversion rate", "accent-brick");

    var statusLabels = Object.keys(stats.by_status);
    var ctx1 = document.getElementById("chartStatus").getContext("2d");
    if(charts.status) charts.status.destroy();
    charts.status = new Chart(ctx1, {
      type:"doughnut",
      data:{ labels: statusLabels, datasets:[{ data: statusLabels.map(function(s){return stats.by_status[s];}), backgroundColor: statusLabels.map(function(s){return STATUS_HEX[s]||"#999";}), borderWidth:0 }] },
      options:{ maintainAspectRatio:false, plugins:{ legend:{ position:"bottom", labels:{boxWidth:10, font:{size:11}, color:"#8A8578"} } } }
    });

    var sourceLabels = Object.keys(stats.by_source);
    var ctx2 = document.getElementById("chartSource").getContext("2d");
    if(charts.source) charts.source.destroy();
    charts.source = new Chart(ctx2, {
      type:"bar",
      data:{ labels: sourceLabels, datasets:[{ data: sourceLabels.map(function(s){return stats.by_source[s];}), backgroundColor: sourceLabels.map(function(s){return SOURCE_HEX[s]||"#999";}), borderRadius:6, maxBarThickness:46 }] },
      options:{ maintainAspectRatio:false, plugins:{ legend:{display:false} }, scales:{ y:{ beginAtZero:true, ticks:{precision:0, color:"#8A8578"}, grid:{color:"rgba(120,120,120,0.1)"} }, x:{ ticks:{color:"#8A8578"}, grid:{display:false} } } }
    });

    var counsellorRows = stats.by_counsellor || [];
    var cLabels = counsellorRows.map(function(r){ return r.counsellor; });
    var ctx3 = document.getElementById("chartCounsellor").getContext("2d");
    if(charts.counsellor) charts.counsellor.destroy();
    charts.counsellor = new Chart(ctx3, {
      type:"bar",
      data:{ labels: cLabels, datasets:[
        { label:"Assigned leads", data: counsellorRows.map(function(r){return r.assigned;}), backgroundColor:"#C9C2AC", borderRadius:6, maxBarThickness:34 },
        { label:"Converted", data: counsellorRows.map(function(r){return r.converted;}), backgroundColor:"#2F6B4F", borderRadius:6, maxBarThickness:34 }
      ]},
      options:{ maintainAspectRatio:false, plugins:{ legend:{position:"bottom", labels:{boxWidth:10, font:{size:11}, color:"#8A8578"}} }, scales:{ y:{beginAtZero:true, ticks:{precision:0, color:"#8A8578"}, grid:{color:"rgba(120,120,120,0.1)"}}, x:{ticks:{color:"#8A8578"}, grid:{display:false}} } }
    });
    }catch(err){
      grid.innerHTML = '<div class="panel error-row" style="grid-column:1/-1;">Dashboard data is unavailable. Check that the server is running.</div>';
      showToast("Could not load dashboard: " + err.message);
    }
  }

  async function renderFollowups(){
    var container = document.getElementById("followupsContainer");
    container.innerHTML = '<div class="panel">Loading follow-ups...</div>';
    var rows;
    try{ rows = await api("/api/leads"); }
    catch(err){ container.innerHTML = '<div class="panel error-row">Could not load follow-ups. Check that the server is running.</div>'; showToast("Could not load follow-ups: " + err.message); return; }
    var withDate = rows.filter(function(l){ return !!l.followup_date; });
    withDate.sort(function(a,b){ return a.followup_date < b.followup_date ? -1 : 1; });
    var today = todayStr();
    var overdue = withDate.filter(function(l){ return l.followup_date < today; });
    var todayList = withDate.filter(function(l){ return l.followup_date === today; });
    var upcoming = withDate.filter(function(l){ return l.followup_date > today; });

    container.innerHTML = "";
    if(withDate.length === 0){
      container.innerHTML = '<div class="panel">No follow-ups scheduled. Open a lead from "All leads" to set one.</div>';
      return;
    }
    container.appendChild(fuGroup("Overdue", overdue, "overdue"));
    container.appendChild(fuGroup("Today", todayList, "today"));
    container.appendChild(fuGroup("Upcoming", upcoming, "upcoming"));
  }

  function fuGroup(title, list, cls){
    var wrap = document.createElement("div"); wrap.className = "fu-group";
    var head = document.createElement("div"); head.className = "fu-group-title";
    head.innerHTML = title + ' <span class="count">'+list.length+'</span>';
    wrap.appendChild(head);
    if(list.length === 0){
      var empty = document.createElement("div");
      empty.style.cssText = "color:var(--muted); font-size:13px; padding:4px 0 2px;";
      empty.textContent = "Nothing here right now.";
      wrap.appendChild(empty);
      return wrap;
    }
    list.forEach(function(l){
      var card = document.createElement("div"); card.className = "fu-card " + cls;
      card.innerHTML =
        '<div class="fu-main"><div class="name">'+escapeHtml(l.name)+'</div>'+
        '<div class="meta">'+escapeHtml(l.course||"—")+' · '+escapeHtml(l.counsellor||"—")+' · <span class="badge" style="background:'+STATUS_SOFT[l.status]+'; color:'+STATUS_COLOR[l.status]+';">'+l.status+'</span></div></div>'+
        '<div class="fu-date '+cls+'">'+fmtDate(l.followup_date)+'</div>';
      card.addEventListener("click", function(){ openDrawer(l.id); });
      wrap.appendChild(card);
    });
    return wrap;
  }

  function setupDrawer(){
    document.getElementById("closeDrawer").addEventListener("click", closeDrawer);
    document.getElementById("overlay").addEventListener("click", closeDrawer);
    document.getElementById("drawerCounsellor").addEventListener("change", async function(){
      try{ await api("/api/leads/"+activeLeadId, { method:"PUT", body: JSON.stringify({counsellor_id: this.value}) }); refreshAfterChange(); }
      catch(err){ showToast("Update failed: " + err.message); }
    });
    document.getElementById("drawerFollowup").addEventListener("change", async function(){
      try{ await api("/api/leads/"+activeLeadId, { method:"PUT", body: JSON.stringify({followup_date: this.value}) }); showToast("Follow-up date updated"); refreshAfterChange(); }
      catch(err){ showToast("Update failed: " + err.message); }
    });
    document.getElementById("addNoteBtn").addEventListener("click", async function(){
      var box = document.getElementById("drawerNoteInput");
      var text = box.value.trim();
      if(!text) return;
      try{
        await api("/api/leads/"+activeLeadId+"/notes", { method:"POST", body: JSON.stringify({note:text}) });
        box.value = "";
        showToast("Note added");
        await loadNotesInto(activeLeadId);
      }catch(err){ showToast("Could not add note: " + err.message); }
    });
    document.getElementById("removeLeadBtn").addEventListener("click", async function(){
      if(!activeLeadId) return;
      if(!confirm("Remove this lead from the CRM? This can't be undone.")) return;
      try{
        await api("/api/leads/"+activeLeadId, { method:"DELETE" });
        closeDrawer();
        showToast("Lead removed");
        refreshAfterChange();
      }catch(err){ showToast("Could not remove: " + err.message); }
    });
  }

  function currentViewName(){
    var active = document.querySelector(".view.active");
    return active ? active.id.replace("view-","") : "dashboard";
  }

  function refreshAfterChange(){
    var v = currentViewName();
    if(v === "dashboard") renderDashboard();
    if(v === "leads") loadAndRenderLeads();
    if(v === "followups") renderFollowups();
  }

  async function openDrawer(id){
    activeLeadId = id;
    var rows = await api("/api/leads");
    var lead = rows.find(function(l){ return l.id === id; });
    if(!lead) return;

    document.getElementById("drawerName").textContent = lead.name;
    document.getElementById("drawerCourse").textContent = lead.course || "—";
    document.getElementById("drawerPhone").textContent = lead.phone || "—";
    document.getElementById("drawerEmail").textContent = lead.email || "—";
    document.getElementById("drawerCity").textContent = lead.city || "—";
    document.getElementById("drawerSource").textContent = lead.source || "—";
    document.getElementById("drawerCreated").textContent = lead.created_at ? new Date(lead.created_at).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}) : "—";
    document.getElementById("drawerCounsellor").value = lead.counsellor_id;
    document.getElementById("drawerFollowup").value = lead.followup_date || "";

    var pillRow = document.getElementById("statusPillRow");
    pillRow.innerHTML = "";
    meta.statuses.forEach(function(s){
      var pill = document.createElement("button");
      pill.type = "button";
      pill.className = "status-pill" + (s === lead.status ? " selected" : "");
      pill.textContent = s;
      if(s === lead.status){ pill.style.background = STATUS_HEX[s]; }
      pill.addEventListener("click", async function(){
        try{
          await api("/api/leads/"+lead.id, { method:"PUT", body: JSON.stringify({status:s}) });
          showToast("Stage updated to " + s);
          openDrawer(lead.id);
          refreshAfterChange();
        }catch(err){ showToast("Update failed: " + err.message); }
      });
      pillRow.appendChild(pill);
    });

    await loadNotesInto(id);
    document.getElementById("overlay").classList.add("show");
    document.getElementById("drawer").classList.add("show");
    document.getElementById("drawer").setAttribute("aria-hidden", "false");
  }

  async function loadNotesInto(leadId){
    var notes = await api("/api/leads/"+leadId+"/notes");
    var box = document.getElementById("notesList");
    if(!notes || notes.length === 0){
      box.innerHTML = '<div style="color:var(--muted); font-size:13px;">No notes logged yet.</div>';
      return;
    }
    box.innerHTML = notes.map(function(n){
      return '<div class="note-item"><div class="note-date">'+fmtDate(n.created_at.slice(0,10))+'</div>'+escapeHtml(n.note)+'</div>';
    }).join("");
  }

  function closeDrawer(){
    document.getElementById("overlay").classList.remove("show");
    document.getElementById("drawer").classList.remove("show");
    document.getElementById("drawer").setAttribute("aria-hidden", "true");
    activeLeadId = null;
  }

  async function init(){
    setTodayLabel();
    try{
      await loadMeta();
      setupNav();
      setupForm();
      setupFilters();
      setupDrawer();
      await renderDashboard();
    }catch(err){
      showToast("Could not connect to the CRM: " + err.message);
    }
  }

  document.addEventListener("keydown", function(e){ if(e.key === "Escape") closeDrawer(); });
  document.addEventListener("DOMContentLoaded", init);
})();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
