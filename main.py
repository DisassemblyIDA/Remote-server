from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta, timezone
import psycopg2
import os

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности в секундах
ACTIVE_DURATION = timedelta(seconds=30)

# Создание таблицы, если не существует
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

# Шаблон HTML
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>License Status</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
            color: #333;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #007BFF;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }
        th {
            background-color: #007BFF;
            color: white;
        }
        .status {
            display: inline-block;
            width: 12px;
            height: 12px;
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
    <h1>License and User Status</h1>
    <table>
        <thead>
            <tr>
                <th>Nickname</th>
                <th>Server</th>
                <th>Status</th>
                <th>License Status</th>
            </tr>
        </thead>
        <tbody id="data-table-body">
            <tr><td colspan="4">Loading data...</td></tr>
        </tbody>
    </table>
    <script>
        function fetchData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.getElementById('data-table-body');
                    tableBody.innerHTML = '';
                    data.forEach(item => {
                        const row = document.createElement('tr');
                        const statusClass = item.active ? 'active' : 'inactive';
                        const licenseClass = item.license_active ? 'license-active' : 'license-inactive';
                        row.innerHTML = `
                            <td>${item.nickname}</td>
                            <td>${item.server}</td>
                            <td><span class="status ${statusClass}"></span></td>
                            <td class="${licenseClass}">${item.license_active ? 'Active' : 'Inactive'}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                })
                .catch(err => console.error('Error fetching data:', err));
        }
        setInterval(fetchData, 5000);
        fetchData();
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    deviceid = data.get("deviceid")
    ip = data.get("ip")
    server = data.get("server")
    nickname = data.get("nickname")
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    if not deviceid:
        return jsonify({"error": "deviceid is required"}), 400

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

@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now(timezone.utc)
    cur.execute("SELECT nickname, server, license_active, last_active FROM user_data;")
    rows = cur.fetchall()

    response = []
    for nickname, server, license_active, last_active in rows:
        # Приведение last_active к timezone-aware
        if last_active.tzinfo is None:
            last_active = last_active.replace(tzinfo=timezone.utc)
        active = (current_time - last_active) < ACTIVE_DURATION
        response.append({
            "nickname": nickname,
            "server": server,
            "active": active,
            "license_active": license_active
        })

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
