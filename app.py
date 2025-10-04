# app.py
from flask import Flask, request, redirect, session
from markupsafe import escape
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "changeme123"  # Später besser als Umgebungsvariable speichern

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

# Helper: HTML Templates mit CSS
def render_template(content):
    return f"""
    <html>
    <head>
        <title>Chatter</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f0f2f5;
                padding: 20px;
            }}
            h2 {{
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            input[type=text], input[type=password] {{
                width: 100%;
                padding: 8px;
                margin: 5px 0;
                border-radius: 4px;
                border: 1px solid #ccc;
            }}
            button {{
                padding: 8px 16px;
                margin-top: 5px;
                border: none;
                border-radius: 4px;
                background-color: #4CAF50;
                color: white;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #45a049;
            }}
            .post {{
                background-color: #f9f9f9;
                padding: 10px;
                margin: 10px 0;
                border-radius: 4px;
            }}
            .own-post {{
                background-color: #d0f0c0;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            hr {{
                border: 0;
                border-top: 1px solid #eee;
                margin: 15px 0;
            }}
        </style>
    </head>
    <body>
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
    c.execute("SELECT posts.text, posts.timestamp, users.username FROM posts JOIN users ON posts.user_id = users.id ORDER BY posts.id DESC")
    all_posts = c.fetchall()

    # Eigene Posts
    c.execute("SELECT posts.text, posts.timestamp FROM posts JOIN users ON posts.user_id = users.id WHERE users.username=? ORDER BY posts.id DESC", (session['username'],))
    own_posts = c.fetchall()
    conn.close()

    feed_html = f"""
    <div class="header">
        <h2>Chatter Feed</h2>
        <p>Angemeldet als <b>{escape(session['username'])}</b> | <a href='/logout'>Logout</a></p>
    </div>

    <form method='POST' action='/post'>
        <input name='text' placeholder='Neuer Post' required>
        <button type='submit'>Posten</button>
    </form>
    <hr>

    <h3>Eigene Posts</h3>
    """
    for text, timestamp in own_posts:
        feed_html += f"<div class='post own-post'>{escape(timestamp)}: {escape(text)}</div>"

    feed_html += "<hr><h3>Allgemeiner Feed</h3>"
    for text, timestamp, username in all_posts:
        feed_html += f"<div class='post'><b>{escape(username)}</b> ({timestamp}): {escape(text)}</div>"

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
