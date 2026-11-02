import os, secrets, sqlite3
from flask import Flask, g, redirect, render_template_string, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-only-change-this")
DB = os.environ.get("DATABASE_PATH", "data/notes.db")


def db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    connection = g.pop("db", None)
    if connection:
        connection.close()


with app.app_context():
    db().executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            body TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    """)

PAGE = """<!doctype html><title>Notes Board</title>
<style>body{font:16px system-ui;background:#f3f6fb;color:#17243a;margin:0}main{max-width:760px;margin:50px auto;padding:28px;background:white;border-radius:16px;box-shadow:0 8px 30px #17304a18}h1{color:#2456a6}.bar,form{display:flex;gap:10px;align-items:center;margin:12px 0}input,button{font:inherit;padding:10px;border:1px solid #ccd5e2;border-radius:8px}input{flex:1}button{background:#2456a6;color:white;border:0;cursor:pointer}.note{padding:12px;background:#f3f6fb;border-radius:8px;margin:10px 0}.inline{display:inline}a{color:#2456a6}</style>
<main><h1>Notes Board</h1><p>Private notes, saved to SQLite.</p>
{% for msg in get_flashed_messages() %}<p>{{msg}}</p>{% endfor %}
{% if user %}<p>Signed in as <b>{{user}}</b> · <a href="{{url_for('logout')}}">Log out</a></p>
<form method="post" action="{{url_for('add')}}"><input type="hidden" name="csrf" value="{{csrf}}"><input name="body" maxlength="500" placeholder="Write a note…" required><button>Add note</button></form>
{% for n in notes %}<div class="note">{{n.body}} <form class="inline" method="post" action="{{url_for('delete', note_id=n.id)}}"><input type="hidden" name="csrf" value="{{csrf}}"><button>Delete</button></form></div>{% else %}<p>No notes yet.</p>{% endfor %}
{% else %}<h2>Sign in</h2><form method="post" action="{{url_for('login')}}"><input type="hidden" name="csrf" value="{{csrf}}"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Log in</button></form>
<h2>Create account</h2><form method="post" action="{{url_for('register')}}"><input type="hidden" name="csrf" value="{{csrf}}"><input name="username" placeholder="Username" required><input name="password" type="password" minlength="8" placeholder="Password (8+ characters)" required><button>Register</button></form>{% endif %}</main>"""


def token():
    session.setdefault("csrf", secrets.token_urlsafe(32))
    return session["csrf"]


@app.before_request
def protect_posts():
    if request.method == "POST" and not secrets.compare_digest(request.form.get("csrf", ""), session.get("csrf", "")):
        return "Invalid form token", 400


@app.get("/")
def home():
    notes = db().execute("SELECT id,body FROM notes WHERE user_id=? ORDER BY id DESC", (session["uid"],)).fetchall() if session.get("uid") else []
    return render_template_string(PAGE, user=session.get("username"), notes=notes, csrf=token())


@app.post("/register")
def register():
    username, password = request.form.get("username", "").strip(), request.form.get("password", "")
    if not username or len(username) > 40 or len(password) < 8:
        return "Choose a username (1–40 characters) and an 8+ character password", 400
    try:
        cur = db().execute("INSERT INTO users(username,password_hash) VALUES (?,?)", (username, generate_password_hash(password)))
        db().commit()
        session.update(uid=cur.lastrowid, username=username)
        session["csrf"] = secrets.token_urlsafe(32)
        return redirect(url_for("home"))
    except sqlite3.IntegrityError:
        return "That username is already taken", 409


@app.post("/login")
def login():
    user = db().execute("SELECT * FROM users WHERE username=?", (request.form.get("username", "").strip(),)).fetchone()
    if not user or not check_password_hash(user["password_hash"], request.form.get("password", "")):
        return "Incorrect username or password", 401
    session.clear()
    session.update(uid=user["id"], username=user["username"], csrf=secrets.token_urlsafe(32))
    return redirect(url_for("home"))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.post("/notes")
def add():
    if not session.get("uid"):
        return redirect(url_for("home"))
    body = request.form.get("body", "").strip()
    if body:
        db().execute("INSERT INTO notes(user_id,body) VALUES (?,?)", (session["uid"], body[:500]))
        db().commit()
    return redirect(url_for("home"))


@app.post("/notes/<int:note_id>/delete")
def delete(note_id):
    if session.get("uid"):
        db().execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, session["uid"]))
        db().commit()
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
