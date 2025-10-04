# app.py
from flask import Flask, request, redirect, session
from markupsafe import escape
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

# Version aus Datei lesen
def get_version():
    try:
        with open("VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect("social.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password_hash TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                 )''')
    conn.commit()
    conn.close()

init_db()

# HTML Template Helper mit Design + Plattformnamen + Version
def render_template(content):
    version = get_version()
    return f"""
    <html>
    <head>
        <title>Chatter</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #e8eff6;
                margin: 0;
                padding: 0;
            }}
            header {{
                background-color: #4267B2;
                color: white;
                padding: 15px 20px;
                display: flex;
                flex-direction: column;
                align-items: flex-start;
            }}
            header h1 {{
                margin: 0;
                font-size: 28px;
            }}
            header small {{
                font-size: 12px;
                color: #d0d8f0;
            }}
            .container {{
                max-width: 700px;
                margin: 30px auto;
                background-color: #fff;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            input[type=text], input[type=password] {{
                width: 100%;
                padding: 10px;
                margin: 8px 0;
                border-radius: 6px;
                border: 1px solid #ccc;
                box-sizing: border-box;
            }}
            button {{
                padding: 10px 18px;
                border: none;
                border-radius: 6px;
                background-color: #4267B2;
                color: white;
                cursor: pointer;
                margin-top: 5px;
            }}
            button:hover {{
                background-color: #365899;
            }}
            .post {{
                background-color: #f1f3f6;
                padding: 12px;
                margin: 10px 0;
                border-radius: 8px;
                position: relative;
            }}
            .own-post {{
                background-color: #d9f0d9;
            }}
            .delete-btn {{
                position: absolute;
                top: 8px;
                right: 8px;
                background-color: #ff4d4f;
                border: none;
                color: white;
                padding: 2px 6px;
                font-size: 12px;
                border-radius: 4px;
                cursor: pointer;
            }}
            .delete-btn:hover {{
                background-color: #cc0000;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            a {{
                color: #4267B2;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            hr {{
                border: 0;
                border-top: 1px solid #eee;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
        <header>
            <h1>Chatter</h1>
            <small>v{version}</small>
        </header>
        <div class="container">
            {content}
        </div>
    </body>
    </html>
    """

# Feed-Seite
@app.route("/")
def index():
    if 'username' not in session:
        return redirect("/login")

    conn = sqlite3.connect("social.db")
    c = conn.cursor()

    # Allgemeiner Feed
    c.execute("SELECT posts.id, posts.text, posts.timestamp, users.username FROM posts JOIN users ON posts.user_id = users.id ORDER BY posts.id DESC")
    all_posts = c.fetchall()

    # Eigene Posts
    c.execute("SELECT posts.id, posts.text, posts.timestamp FROM posts JOIN users ON posts.user_id = users.id WHERE users.username=? ORDER BY posts.id DESC", (session['username'],))
    own_posts = c.fetchall()
    conn.close()

    feed_html = f"""
    <div class="header">
        <p>Angemeldet als <b>{escape(session['username'])}</b> | <a href='/logout'>Logout</a></p>
    </div>

    <form method='POST' action='/post'>
        <input name='text' placeholder='Neuer Post' required>
        <button type='submit'>Posten</button>
    </form>
    <hr>

    <h3>Eigene Posts</h3>
    """
    for post_id, text, timestamp in own_posts:
        feed_html += f"""
        <div class='post own-post'>
            {escape(timestamp)}: {escape(text)}
            <form method='POST' action='/delete' style='display:inline;'>
                <input type='hidden' name='post_id' value='{post_id}'>
                <button type='submit' class='delete-btn'>Löschen</button>
            </form>
        </div>"""

    feed_html += "<hr><h3>Allgemeiner Feed</h3>"
    for post_id, text, timestamp, username in all_posts:
        cls = "own-post" if username == session['username'] else ""
        feed_html += f"<div class='post {cls}'><b>{escape(username)}</b> ({timestamp}): {escape(text)}</div>"

    return render_template(feed_html)

# Neuer Post
@app.route("/post", methods=["POST"])
def post():
    if 'username' not in session:
        return redirect("/login")
    text = request.form['text']
    conn = sqlite3.connect("social.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username=?", (session['username'],))
    user_id = c.fetchone()[0]
    c.execute("INSERT INTO posts (user_id, text, timestamp) VALUES (?, ?, ?)",
              (user_id, text, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return redirect("/")

# Post löschen
@app.route("/delete", methods=["POST"])
def delete_post():
    if 'username' not in session:
        return redirect("/login")
    post_id = request.form['post_id']
    conn = sqlite3.connect("social.db")
    c = conn.cursor()
    # Prüfen, ob der Post dem aktuellen User gehört
    c.execute("SELECT users.username FROM posts JOIN users ON posts.user_id = users.id WHERE posts.id=?", (post_id,))
    owner = c.fetchone()
    if owner and owner[0] == session['username']:
        c.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
    conn.close()
    return redirect("/")

# Registrierung
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        try:
            conn = sqlite3.connect("social.db")
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                      (username, password_hash))
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return render_template("<p>Username existiert schon!</p><a href='/register'>Zurück</a>")

    return render_template("""
    <h2>Registrieren</h2>
    <form method='POST'>
        <input name='username' placeholder='Username' required><br>
        <input type='password' name='password' placeholder='Passwort' required><br>
        <button type='submit'>Registrieren</button>
    </form>
    <a href='/login'>Login</a>
    """)

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("social.db")
        c = conn.cursor()
        c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
        result = c.fetchone()
        conn.close()
        if result and check_password_hash(result[0], password):
            session['username'] = username
            return redirect("/")
        return render_template("<p>Login fehlgeschlagen!</p><a href='/login'>Zurück</a>")

    return render_template("""
    <h2>Login</h2>
    <form method='POST'>
        <input name='username' placeholder='Username' required><br>
        <input type='password' name='password' placeholder='Passwort' required><br>
        <button type='submit'>Login</button>
    </form>
    <a href='/register'>Registrieren</a>
    """)

# Logout
@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
