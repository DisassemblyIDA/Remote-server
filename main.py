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
            real_nickname TEXT DEFAULT 'None',  -- Новый столбец
            license_active BOOLEAN NOT NULL,
            last_active TIMESTAMP NOT NULL,
            allowed BOOLEAN DEFAULT FALSE
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
                <th>Real Nickname</th>  <!-- Новый столбец -->
                <th>Server</th>
                <th>Status</th>
                <th>License Status</th>
            </tr>
        </thead>
        <tbody id="data-table-body">
            <tr><td colspan="5">Loading data...</td></tr>
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
                        row.innerHTML = 
                            `<td>${item.nickname}</td>
                            <td>${item.real_nickname}</td>
                            <td>${item.server}</td>
                            <td><span class="status ${statusClass}"></span></td>
                            <td class="${licenseClass}">${item.license_active ? 'Active' : 'Inactive'}</td>`;
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
    real_nickname = data.get("real_nickname", "None")  # Получение real_nickname, по умолчанию "None"
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    if not deviceid:
        return jsonify({"error": "deviceid is required"}), 400

    try:
        # Если deviceid равен "-", вставляем с уникальностью по IP
        if deviceid == "-":
            # Проверка, если уже существует запись с таким ip
            cur.execute("""
                INSERT INTO user_data (deviceid, ip, server, nickname, real_nickname, license_active, last_active, allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip) WHERE deviceid = '-' DO NOTHING;
            """, (deviceid, ip, server, nickname, real_nickname, license_active, last_active, False))
        else:
            # Для других случаев — обычная вставка с обновлением в случае конфликта
            cur.execute("""
                INSERT INTO user_data (deviceid, ip, server, nickname, real_nickname, license_active, last_active, allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (deviceid) DO UPDATE SET
                ip = EXCLUDED.ip,
                server = EXCLUDED.server,
                nickname = EXCLUDED.nickname,
                real_nickname = EXCLUDED.real_nickname,
                license_active = EXCLUDED.license_active,
                last_active = EXCLUDED.last_active;
            """, (deviceid, ip, server, nickname, real_nickname, license_active, last_active, False))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except psycopg2.Error as e:
        # Обработка ошибки в транзакции
        conn.rollback()  # Откатить транзакцию в случае ошибки
        print("Error occurred while receiving data:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now(timezone.utc)

    try:
        cur.execute("SELECT nickname, real_nickname, server, license_active, last_active FROM user_data;")
        rows = cur.fetchall()

        response = []
        for nickname, real_nickname, server, license_active, last_active in rows:
            # Приведение last_active к timezone-aware
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            active = (current_time - last_active) < ACTIVE_DURATION
            response.append({
                "nickname": nickname,
                "real_nickname": real_nickname,  # Добавление real_nickname в ответ
                "server": server,
                "active": active,
                "license_active": license_active
            })

        return jsonify(response)
    
    except psycopg2.Error as e:
        # Обработка ошибки в транзакции
        conn.rollback()  # Откатить транзакцию в случае ошибки
        print("Error occurred while fetching data:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/check_ip/<deviceid>', methods=['GET'])
def check_ip(deviceid):
    # Проверка существования deviceid в базе данных и его значения
    cur.execute("SELECT allowed FROM user_data WHERE deviceid = %s;", (deviceid,))
    result = cur.fetchone()
    if result and result[0]:  # Если allowed == True
        return "1"
    return "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
