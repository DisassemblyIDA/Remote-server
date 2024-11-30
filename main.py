from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta, timezone
import psycopg2
import os

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности
ACTIVE_DURATION = timedelta(seconds=30)

# HTML-шаблон (на английском)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Management</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            color: #333;
            padding: 20px;
        }
        h1 {
            color: #007BFF;
            text-align: center;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }
        th {
            background-color: #007BFF;
            color: #fff;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        .active {
            color: #28a745;
        }
        .inactive {
            color: #dc3545;
        }
    </style>
    <script>
        // Fetch data every 2 seconds
        function fetchData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.getElementById('data-table-body');
                    tableBody.innerHTML = ''; // Clear existing rows
                    if (data.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="4">No data available.</td></tr>';
                    } else {
                        data.forEach(item => {
                            const row = document.createElement('tr');
                            const statusClass = item[3] ? 'active' : 'inactive';
                            row.innerHTML = `
                                <td>${item[0]}</td>
                                <td>${item[1]}</td>
                                <td class="${statusClass}">${item[2]}</td>
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                })
                .catch(error => console.error('Error fetching data:', error));
        }

        setInterval(fetchData, 2000);
        window.onload = fetchData;
    </script>
</head>
<body>
    <div class="container">
        <h1>Device Management</h1>
        <table>
            <thead>
                <tr>
                    <th>Device ID</th>
                    <th>Nickname</th>
                    <th>License Status</th>
                </tr>
            </thead>
            <tbody id="data-table-body">
                <tr><td colspan="4">No data available.</td></tr>
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# Создание таблицы, если не существует
def create_table():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            deviceid TEXT PRIMARY KEY,
            nickname TEXT NOT NULL,
            activated BOOLEAN NOT NULL,
            last_active TIMESTAMP
        );
    """)
    conn.commit()

create_table()

@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_data(as_text=True)
    print(f"Received data: {data}")  # Логирование полученных данных
    if data:
        ip, server, nickname, deviceid, status = data.split(" ", 4)
        last_active = datetime.now()

        # Сохранение данных в БД
        cur.execute("""
            INSERT INTO user_data (deviceid, nickname, activated, last_active)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (deviceid) DO UPDATE SET
            nickname = EXCLUDED.nickname,
            activated = EXCLUDED.activated,
            last_active = EXCLUDED.last_active;
        """, (deviceid, nickname, status == 'activated', last_active))
        conn.commit()
    
    return jsonify({"status": "success", "data": data}), 201

@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now(timezone.utc)
    cur.execute("SELECT * FROM user_data;")
    users = cur.fetchall()

    response_data = []
    for deviceid, nickname, activated, last_active in users:
        if isinstance(last_active, datetime):
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            time_diff = current_time - last_active
            status = time_diff < ACTIVE_DURATION  # Активен ли пользователь
        else:
            status = False

        license_status = "Activated" if activated else "Deactivated"
        response_data.append([deviceid, nickname, license_status, status])
    
    return jsonify(response_data)

@app.route('/check_device/<deviceid>', methods=['GET'])
def check_device(deviceid):
    cur.execute("SELECT 1 FROM user_data WHERE deviceid = %s;", (deviceid,))
    exists = cur.fetchone()
    return jsonify({"exists": bool(exists)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
