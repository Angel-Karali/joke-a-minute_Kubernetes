import os
import time
import redis
import mysql.connector
from flask import Flask, jsonify, render_template_string, request, redirect, url_for


app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "mysql")
DB_USER = os.getenv("DB_USER", "joke_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "joke_pass123")
DB_NAME = os.getenv("DB_NAME", "jokes_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

APP_PORT = int(os.getenv("APP_PORT", "5000"))

# Database configuration
db_config = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "port": DB_PORT
}

# Redis configuration
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

# Main page HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Joke-a-Minute 😂</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .nav {
            text-align: center;
            margin-bottom: 30px;
        }

        .nav a {
            display: inline-block;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.95);
            color: #667eea;
            text-decoration: none;
            border-radius: 15px;
            margin: 0 10px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }

        .nav a:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 50px 40px;
            max-width: 600px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        }

        h1 {
            color: #667eea;
            font-size: 3em;
            text-align: center;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.1);
        }

        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }

        .joke-container {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            min-height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .joke-container::before {
            content: '"';
            position: absolute;
            top: -20px;
            left: 20px;
            font-size: 120px;
            color: rgba(102, 126, 234, 0.1);
            font-family: Georgia, serif;
        }

        .joke-text {
            font-size: 1.4em;
            color: #333;
            text-align: center;
            line-height: 1.6;
            position: relative;
            z-index: 1;
        }

        .loading {
            color: #999;
            font-style: italic;
        }

        .btn {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 15px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
        }

        .btn:active {
            transform: translateY(0);
        }

        .stats {
            display: flex;
            justify-content: space-around;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }

        .stat {
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }

        .stat-label {
            color: #999;
            font-size: 0.9em;
            margin-top: 5px;
        }

        .cache-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-left: 10px;
        }

        .cached {
            background: #4caf50;
            box-shadow: 0 0 10px #4caf50;
        }

        .fresh {
            background: #ff9800;
            box-shadow: 0 0 10px #ff9800;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .fade-in {
            animation: fadeIn 0.5s ease;
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">🎲 Random Joke</a>
        <a href="/add">➕ Add Joke</a>
        <a href="/manage">📋 Manage Jokes</a>
    </div>

    <div class="container">
        <h1>😂 Joke-a-Minute</h1>
        <p class="subtitle">Your daily dose of dad jokes, cached fresh!</p>

        <div class="joke-container">
            <div id="joke" class="joke-text loading">Click the button to get a joke!</div>
        </div>

        <button class="btn" onclick="getJoke()">Get New Joke 🎲</button>

        <div class="stats">
            <div class="stat">
                <span id="source" class="stat-value">-</span>
                <span class="stat-label">Source</span>
            </div>
            <div class="stat">
                <span id="responseTime" class="stat-value">-</span>
                <span class="stat-label">Response Time</span>
            </div>
        </div>
    </div>

    <script>
        async function getJoke() {
            const jokeEl = document.getElementById('joke');
            const sourceEl = document.getElementById('source');
            const timeEl = document.getElementById('responseTime');

            jokeEl.className = 'joke-text loading';
            jokeEl.textContent = 'Loading joke...';

            const startTime = performance.now();

            try {
                const response = await fetch('/joke');
                const data = await response.json();
                const endTime = performance.now();
                const responseTime = Math.round(endTime - startTime);

                jokeEl.className = 'joke-text fade-in';
                jokeEl.textContent = data.joke;

                sourceEl.innerHTML = data.source === 'cache' 
                    ? 'Redis <span class="cache-indicator cached"></span>' 
                    : 'MySQL <span class="cache-indicator fresh"></span>';
                timeEl.textContent = responseTime + 'ms';
            } catch (error) {
                jokeEl.className = 'joke-text';
                jokeEl.textContent = 'Oops! Failed to fetch a joke. Try again!';
            }
        }

        // Load a joke on page load
        window.onload = getJoke;
    </script>
</body>
</html>
'''

# Add joke page HTML template
ADD_JOKE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Add Joke 😂</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .nav {
            text-align: center;
            margin-bottom: 30px;
        }

        .nav a {
            display: inline-block;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.95);
            color: #667eea;
            text-decoration: none;
            border-radius: 15px;
            margin: 0 10px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }

        .nav a:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 50px 40px;
            max-width: 600px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        h1 {
            color: #667eea;
            font-size: 2.5em;
            text-align: center;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            color: #333;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 1.1em;
        }

        textarea {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 15px;
            font-size: 1.1em;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            resize: vertical;
            min-height: 120px;
            transition: border-color 0.3s ease;
        }

        textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            width: 100%;
            padding: 18px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 15px;
            font-size: 1.2em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
        }

        .btn:active {
            transform: translateY(0);
        }

        .success-message {
            background: #4caf50;
            color: white;
            padding: 15px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">🎲 Random Joke</a>
        <a href="/add">➕ Add Joke</a>
        <a href="/manage">📋 Manage Jokes</a>
    </div>

    <div class="container">
        <h1>➕ Add New Joke</h1>
        <p class="subtitle">Share your best dad joke!</p>

        {% if success %}
        <div class="success-message">
            ✅ Joke added successfully!
        </div>
        {% endif %}

        <form method="POST" action="/add">
            <div class="form-group">
                <label for="joke">Your Joke:</label>
                <textarea id="joke" name="joke" placeholder="Why did the chicken cross the road? ..." required></textarea>
            </div>

            <button type="submit" class="btn">Add Joke 🎉</button>
        </form>
    </div>
</body>
</html>
'''

# Manage jokes page HTML template
MANAGE_JOKES_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Manage Jokes 😂</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .nav {
            text-align: center;
            margin-bottom: 30px;
        }

        .nav a {
            display: inline-block;
            padding: 12px 30px;
            background: rgba(255, 255, 255, 0.95);
            color: #667eea;
            text-decoration: none;
            border-radius: 15px;
            margin: 0 10px;
            font-weight: bold;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }

        .nav a:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 50px 40px;
            max-width: 900px;
            margin: 0 auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }

        h1 {
            color: #667eea;
            font-size: 2.5em;
            text-align: center;
            margin-bottom: 10px;
        }

        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }

        .joke-count {
            text-align: center;
            color: #667eea;
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 30px;
        }

        .jokes-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 15px;
        }

        .jokes-table tr {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 15px;
        }

        .jokes-table td {
            padding: 20px;
            vertical-align: middle;
        }

        .jokes-table td:first-child {
            border-radius: 15px 0 0 15px;
            width: 60px;
            text-align: center;
            font-weight: bold;
            color: #667eea;
            font-size: 1.2em;
        }

        .jokes-table td:nth-child(2) {
            font-size: 1.1em;
            color: #333;
            line-height: 1.6;
        }

        .jokes-table td:last-child {
            border-radius: 0 15px 15px 0;
            text-align: right;
            width: 100px;
        }

        .delete-btn {
            padding: 10px 20px;
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 3px 10px rgba(255, 107, 107, 0.4);
        }

        .delete-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 107, 107, 0.6);
        }

        .delete-btn:active {
            transform: translateY(0);
        }

        .no-jokes {
            text-align: center;
            color: #999;
            font-size: 1.2em;
            padding: 40px;
        }
    </style>
</head>
<body>
    <div class="nav">
        <a href="/">🎲 Random Joke</a>
        <a href="/add">➕ Add Joke</a>
        <a href="/manage">📋 Manage Jokes</a>
    </div>

    <div class="container">
        <h1>📋 Manage Jokes</h1>
        <p class="subtitle">View and delete jokes from the database</p>

        <div class="joke-count">
            Total Jokes: {{ jokes|length }}
        </div>

        {% if jokes %}
        <table class="jokes-table">
            {% for joke in jokes %}
            <tr>
                <td>#{{ joke.id }}</td>
                <td>{{ joke.text }}</td>
                <td>
                    <form method="POST" action="/delete/{{ joke.id }}" style="display: inline;" onsubmit="return confirm('Are you sure you want to delete this joke?');">
                        <button type="submit" class="delete-btn">🗑️ Delete</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="no-jokes">
            No jokes found. Add some jokes to get started! 🎭
        </div>
        {% endif %}
    </div>
</body>
</html>
'''


def get_db_connection():
    return mysql.connector.connect(**db_config)


@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)


@app.route('/joke')
def get_joke():
    # Check Redis cache first
    cached_joke = redis_client.get('joke:current')

    if cached_joke:
        return jsonify({
            'joke': cached_joke,
            'source': 'cache',
            'timestamp': time.time()
        })

    # Cache miss - fetch from database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get a random joke
    cursor.execute("SELECT text FROM jokes ORDER BY RAND() LIMIT 1")
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result:
        joke_text = result[0]
        # Cache the joke for 60 seconds
        redis_client.setex('joke:current', 10, joke_text)

        return jsonify({
            'joke': joke_text,
            'source': 'database',
            'timestamp': time.time()
        })

    return jsonify({
        'joke': 'No jokes available!',
        'source': 'error',
        'timestamp': time.time()
    }), 404


@app.route('/add', methods=['GET', 'POST'])
def add_joke():
    success = False

    if request.method == 'POST':
        joke_text = request.form.get('joke', '').strip()

        if joke_text:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO jokes (text) VALUES (%s)", (joke_text,))
            conn.commit()

            cursor.close()
            conn.close()

            # Clear cache so new joke can be selected
            redis_client.delete('joke:current')

            success = True

    return render_template_string(ADD_JOKE_TEMPLATE, success=success)


@app.route('/manage')
def manage_jokes():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, text FROM jokes ORDER BY id")
    jokes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template_string(MANAGE_JOKES_TEMPLATE, jokes=jokes)


@app.route('/delete/<int:joke_id>', methods=['POST'])
def delete_joke(joke_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM jokes WHERE id = %s", (joke_id,))
    conn.commit()

    cursor.close()
    conn.close()

    # Clear cache after deletion
    redis_client.delete('joke:current')

    return redirect(url_for('manage_jokes'))


@app.route('/health')
def health():
    try:
        # Check MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jokes")
        joke_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        mysql_status = 'ok'
    except:
        mysql_status = 'error'
        joke_count = 0

    try:
        # Check Redis
        redis_client.ping()
        redis_status = 'ok'
    except:
        redis_status = 'error'

    return jsonify({
        'status': 'healthy' if mysql_status == 'ok' and redis_status == 'ok' else 'unhealthy',
        'mysql': mysql_status,
        'redis': redis_status,
        'total_jokes': joke_count
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=APP_PORT, debug=False, use_reloader=False)