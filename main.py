from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import psycopg2
import os

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности пользователя
ACTIVE_DURATION = timedelta(seconds=30)

# HTML-шаблон
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Data</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            color: #343a40;
            padding: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border: 1px solid #dee2e6;
        }
        th {
            background-color: #343a40;
            color: #fff;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .active {
            background-color: green;
        }
        .inactive {
            background-color: red;
        }
        .license-active {
            color: green;
        }
        .license-inactive {
            color: red;
        }
    </style>
</head>
<body>
    <h1>User Data</h1>
    <table>
        <thead>
            <tr>
                <th>Server</th>
                <th>Nickname</th>
                <th>Status</th>
                <th>License Status</th>
            </tr>
        </thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.server }}</td>
                <td>{{ user.nickname }}</td>
                <td><span class="status-dot {{ 'active' if user.active else 'inactive' }}"></span></td>
                <td class="{{ 'license-active' if user.license_active else 'license-inactive' }}">
                    {{ 'Active' if user.license_active else 'Inactive' }}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

# Создание таблицы
def create_table():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            deviceid TEXT PRIMARY KEY,
            ip TEXT NOT NULL,
            server TEXT NOT NULL,
            nickname TEXT NOT NULL,
            license_active BOOLEAN NOT NULL,
            last_active TIMESTAMP NOT NULL
        );
    """)
    conn.commit()

create_table()

@app.route('/', methods=['GET'])
def home():
    cur.execute("SELECT server, nickname, license_active, last_active FROM user_data;")
    rows = cur.fetchall()

    current_time = datetime.now()
    users = []
    for server, nickname, license_active, last_active in rows:
        active = (current_time - last_active) <= ACTIVE_DURATION
        users.append({
            "server": server,
            "nickname": nickname,
            "active": active,
            "license_active": license_active
        })
    return render_template_string(HTML_TEMPLATE, users=users)

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.data.decode('utf-8').split()
        if len(data) != 5:
            return jsonify({"error": "Invalid data format"}), 400

        ip, server, nickname, deviceid, license_status = data
        license_active = license_status.lower() == "activated"
        last_active = datetime.now()

        cur.execute("""
            INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (deviceid) DO UPDATE SET
            ip = EXCLUDED.ip,
            server = EXCLUDED.server,
            nickname = EXCLUDED.nickname,
            license_active = EXCLUDED.license_active,
            last_active = EXCLUDED.last_active;
        """, (deviceid, ip, server, nickname, license_active, last_active))
        conn.commit()

        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/check_device/<deviceid>', methods=['GET'])
def check_device(deviceid):
    cur.execute("SELECT 1 FROM user_data WHERE deviceid = %s;", (deviceid,))
    exists = cur.fetchone() is not None
    return jsonify({"exists": exists}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
