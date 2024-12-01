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

# Создание таблицы, триггера и функции, если не существуют
def setup_database():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        deviceid TEXT NOT NULL,
        ip TEXT NOT NULL,
        server TEXT NOT NULL,
        nickname TEXT NOT NULL,
        real_nickname TEXT NOT NULL DEFAULT 'None',
        license_active BOOLEAN NOT NULL,
        last_active TIMESTAMP NOT NULL,
        allowed BOOLEAN DEFAULT FALSE,
        unique_identifier TEXT,
        CONSTRAINT unique_key UNIQUE (unique_identifier)
    );
    """)

    cur.execute("""
    CREATE OR REPLACE FUNCTION update_unique_identifier()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.unique_identifier = CASE
            WHEN NEW.deviceid = '-' THEN NEW.ip
            ELSE NEW.deviceid
        END;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS update_unique_identifier_trigger ON user_data;
    CREATE TRIGGER update_unique_identifier_trigger
    BEFORE INSERT OR UPDATE ON user_data
    FOR EACH ROW EXECUTE FUNCTION update_unique_identifier();
    """)
    conn.commit()

setup_database()

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
        .status-info {
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>License and User Status</h1>
    <table>
        <thead>
            <tr>
                <th>Nickname</th>
                <th>Real Nickname</th>
                <th>Server</th>
                <th>License Status</th>
                <th>Status</th>
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
                    const uniqueUsers = new Map();
                    
                    data.forEach(item => {
                        if (!uniqueUsers.has(item.nickname)) {
                            uniqueUsers.set(item.nickname, item);
                        }
                    });

                    uniqueUsers.forEach(item => {
                        const row = document.createElement('tr');
                        const statusClass = item.active ? 'active' : 'inactive';
                        const licenseClass = item.license_active ? 'license-active' : 'license-inactive';

                        const lastActiveDate = new Date(item.last_active);
                        const formattedDate = lastActiveDate.toLocaleString();

                        let statusText = item.active ? 'Active' : `Inactive | Last active: ${formattedDate}`;

                        row.innerHTML = 
                            `<td>${item.nickname}</td>
                            <td>${item.real_nickname}</td>
                            <td>${item.server}</td>
                            <td class="${licenseClass}">${item.license_active ? 'Active' : 'Inactive'}</td>
                            <td><span class="status ${statusClass}"></span> <span class="status-info">${statusText}</span></td>`;
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

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    deviceid = data.get("deviceid", "-")
    ip = data.get("ip")
    server = data.get("server", "unknown")
    nickname = data.get("nickname", "unknown")
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    if not ip:
        return jsonify({"error": "IP is required"}), 400

    try:
        if deviceid == '-':
            # Проверяем, есть ли запись с таким IP
            cur.execute("SELECT deviceid FROM user_data WHERE unique_identifier = %s;", (ip,))
            result = cur.fetchone()

            if result:
                # Обновляем запись с IP как уникальным идентификатором
                cur.execute("""
                    UPDATE user_data
                    SET server = %s, nickname = %s, license_active = %s, last_active = %s
                    WHERE unique_identifier = %s;
                """, (server, nickname, license_active, last_active, ip))
            else:
                # Создаем новую запись с IP как уникальным идентификатором
                cur.execute("""
                    INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, unique_identifier)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (deviceid, ip, server, nickname, license_active, last_active, ip))
        else:
            # Проверяем, есть ли запись с таким deviceid
            cur.execute("SELECT unique_identifier FROM user_data WHERE unique_identifier = %s;", (deviceid,))
            result = cur.fetchone()

            if result:
                # Обновляем запись с deviceid как уникальным идентификатором
                cur.execute("""
                    UPDATE user_data
                    SET ip = %s, server = %s, nickname = %s, license_active = %s, last_active = %s
                    WHERE unique_identifier = %s;
                """, (ip, server, nickname, license_active, last_active, deviceid))
            else:
                # Проверяем, есть ли запись с таким IP
                cur.execute("SELECT unique_identifier FROM user_data WHERE unique_identifier = %s;", (ip,))
                ip_result = cur.fetchone()

                if ip_result:
                    # Обновляем запись с новым deviceid, меняя уникальный ключ
                    cur.execute("""
                        UPDATE user_data
                        SET deviceid = %s, unique_identifier = %s, server = %s, nickname = %s, license_active = %s, last_active = %s
                        WHERE unique_identifier = %s;
                    """, (deviceid, deviceid, server, nickname, license_active, last_active, ip))
                else:
                    # Создаем новую запись с deviceid как уникальным идентификатором
                    cur.execute("""
                        INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, unique_identifier)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (deviceid, ip, server, nickname, license_active, last_active, deviceid))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except psycopg2.Error as e:
        conn.rollback()
        print("Error occurred while processing data:", e)
        return jsonify({"error": "Internal server error"}), 500


@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now(timezone.utc)

    try:
        cur.execute("SELECT nickname, real_nickname, server, license_active, last_active FROM user_data;")
        rows = cur.fetchall()

        response = []
        for nickname, real_nickname, server, license_active, last_active in rows:
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            active = (current_time - last_active) < ACTIVE_DURATION
            response.append({
                "nickname": nickname,
                "real_nickname": real_nickname,
                "server": server,
                "license_active": license_active,
                "last_active": last_active.isoformat(),
                "active": active
            })

        return jsonify(response)

    except psycopg2.Error as e:
        conn.rollback()
        print("Error occurred while fetching data:", e)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/check_ip/<deviceid>', methods=['GET'])
def check_ip(deviceid):
    cur.execute("SELECT allowed FROM user_data WHERE deviceid = %s;", (deviceid,))
    result = cur.fetchone()
    if result and result[0]:
        return "1"
    return "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
