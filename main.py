from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности
ACTIVE_DURATION = timedelta(seconds=30)

# Настройка базы данных
def setup_database():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        deviceid TEXT PRIMARY KEY,  -- Уникальный идентификатор
        ip TEXT NOT NULL,
        server TEXT NOT NULL,
        nickname TEXT NOT NULL,
        real_nickname TEXT DEFAULT 'None',
        license_active BOOLEAN NOT NULL,
        last_active TIMESTAMP NOT NULL,
        allowed BOOLEAN DEFAULT FALSE,
        unique_identifier TEXT UNIQUE  -- Дополнительный уникальный идентификатор
    );
    """)
    conn.commit()

setup_database()


# HTML для отображения данных
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>License and User Status</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #6a11cb, #2575fc);
            color: #fff;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            width: 90%;
            max-width: 800px;
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
        }
        h1 {
            text-align: center;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
        }
        th {
            background: #444;
            color: #fff;
        }
        tr:nth-child(even) {
            background: rgba(255, 255, 255, 0.1);
        }
        .status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status.active {
            background-color: #4caf50;
        }
        .status.inactive {
            background-color: #f44336;
        }
        .license-active {
            color: #4caf50;
        }
        .license-inactive {
            color: #f44336;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>User Data</h1>
        <table>
            <thead>
                <tr>
                    <th>Nickname</th>
                    <th>Real Nickname</th>
                    <th>Server</th>
                    <th>License</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody id="data-table-body">
                <tr><td colspan="5">Loading...</td></tr>
            </tbody>
        </table>
    </div>
    <script>
        function fetchData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.getElementById('data-table-body');
                    tableBody.innerHTML = '';
                    data.forEach(item => {
                        const statusClass = item.active ? 'active' : 'inactive';
                        const licenseClass = item.license_active ? 'license-active' : 'license-inactive';

                        const lastActiveDate = new Date(item.last_active);
                        const formattedDate = lastActiveDate.toLocaleString();

                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${item.nickname}</td>
                            <td>${item.real_nickname}</td>
                            <td>${item.server}</td>
                            <td class="${licenseClass}">${item.license_active ? 'Active' : 'Inactive'}</td>
                            <td><span class="status ${statusClass}"></span>${item.active ? 'Online' : 'Offline'}</td>
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

@app.route('/')
def home():
    return HTML_TEMPLATE

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    deviceid = data.get("deviceid", "-")
    ip = data.get("ip")
    server = data.get("server", "unknown")
    nickname = data.get("nickname", "unknown")
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    # Логируем запрос
    print(f"Received data: {data}")

    if not ip:
        return jsonify({"error": "IP is required"}), 400

    try:
        unique_identifier = deviceid if deviceid != '-' else ip

        cur.execute("""
        INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, unique_identifier)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (unique_identifier)
        DO UPDATE SET
            ip = EXCLUDED.ip,
            server = EXCLUDED.server,
            nickname = EXCLUDED.nickname,
            license_active = EXCLUDED.license_active,
            last_active = EXCLUDED.last_active;
        """, (deviceid, ip, server, nickname, license_active, last_active, unique_identifier))

        conn.commit()
        print(f"Data inserted/updated successfully for {unique_identifier}")
        return jsonify({"status": "success"}), 201

    except Exception as e:
        conn.rollback()
        print(f"Error inserting data: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now(timezone.utc)
    try:
        # Извлечение всех данных
        cur.execute("""
        SELECT nickname, real_nickname, server, license_active, last_active, allowed
        FROM user_data;
        """)
        rows = cur.fetchall()

        response = []
        for nickname, real_nickname, server, license_active, last_active, allowed in rows:
            active = (current_time - last_active) < ACTIVE_DURATION
            response.append({
                "nickname": nickname,
                "real_nickname": real_nickname,
                "server": server,
                "license_active": license_active,
                "last_active": last_active.isoformat(),
                "active": active,
                "allowed": allowed
            })
        return jsonify(response)

    except psycopg2.Error as e:
        print("Database error:", e)
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
