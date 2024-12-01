from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime, timezone

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Создание таблицы, если не существует
cur.execute("""
CREATE TABLE IF NOT EXISTS user_data (
    deviceid TEXT PRIMARY KEY,
    ip TEXT NOT NULL,
    nickname TEXT NOT NULL,
    last_active TIMESTAMP NOT NULL,
    allowed BOOLEAN DEFAULT FALSE
);
""")
conn.commit()

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    deviceid = data.get("deviceid", "-")
    ip = data.get("ip")
    nickname = data.get("nickname", "unknown")
    allowed = data.get("allowed", False)
    last_active = datetime.now(timezone.utc)

    if deviceid == "-":
        return jsonify({"error": "Invalid deviceid"}), 400

    if not ip:
        return jsonify({"error": "IP is required"}), 400

    try:
        cur.execute("""
        INSERT INTO user_data (deviceid, ip, nickname, last_active, allowed)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (deviceid)
        DO UPDATE SET
            ip = EXCLUDED.ip,
            nickname = EXCLUDED.nickname,
            last_active = EXCLUDED.last_active,
            allowed = EXCLUDED.allowed;
        """, (deviceid, ip, nickname, last_active, allowed))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except psycopg2.Error as e:
        conn.rollback()
        print("Error occurred:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/data', methods=['GET'])
def get_data():
    try:
        cur.execute("SELECT deviceid, ip, nickname, last_active, allowed FROM user_data;")
        rows = cur.fetchall()

        response = [
            {
                "deviceid": row[0],
                "ip": row[1],
                "nickname": row[2],
                "last_active": row[3].isoformat(),
                "license_status": "Active" if row[4] else "Inactive"
            }
            for row in rows
        ]
        return jsonify(response)

    except psycopg2.Error as e:
        conn.rollback()
        print("Error occurred while fetching data:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/', methods=['GET'])
def home():
    html_template = """
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
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
        }
        th {
            background: rgba(255, 255, 255, 0.2);
            color: #fff;
        }
        tr:nth-child(even) {
            background: rgba(255, 255, 255, 0.1);
        }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>User Data</h1>
            <table>
                <thead>
                    <tr>
                        <th>Device ID</th>
                        <th>IP</th>
                        <th>Nickname</th>
                        <th>Last Active</th>
                        <th>License Status</th>
                    </tr>
                </thead>
                <tbody id="data-body">
                    <tr><td colspan="5">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        <script>
            function fetchData() {
                fetch('/data')
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('data-body');
                        tbody.innerHTML = '';
                        data.forEach(item => {
                            const row = document.createElement('tr');
                            row.innerHTML = `
                                <td>${item.deviceid}</td>
                                <td>${item.ip}</td>
                                <td>${item.nickname}</td>
                                <td>${new Date(item.last_active).toLocaleString()}</td>
                                <td>${item.license_status}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    })
                    .catch(err => console.error('Error fetching data:', err));
            }
            fetchData();
            setInterval(fetchData, 5000);
        </script>
    </body>
    </html>
    """
    return html_template

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
