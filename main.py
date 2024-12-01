from flask import Flask, request, jsonify
import os
import psycopg2
from datetime import datetime, timezone, timedelta

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
    <title>License and User Status</title>
    <style>
    /* Общий фон страницы */
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

    /* Контейнер таблицы */
    .container {
        max-width: 90%;
        margin: 20px auto;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
    }

    /* Заголовок */
    h1 {
        text-align: center;
        font-size: 2rem;
        background: linear-gradient(90deg, #6a11cb, #2575fc);
        padding: 15px;
        margin: 0;
        border-bottom: 2px solid rgba(255, 255, 255, 0.2);
        border-top-left-radius: 15px;
        border-top-right-radius: 15px;
        box-shadow: 0 5px 10px rgba(0, 0, 0, 0.3);
    }

    /* Таблица */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 0;
        text-align: left;
    }

    /* Шапка таблицы */
    thead th {
        background: linear-gradient(135deg, #6a11cb, #2575fc);
        color: #fff;
        font-weight: bold;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
    }

    /* Тело таблицы */
    tbody tr {
        background: rgba(255, 255, 255, 0.1);
        transition: background 0.3s ease, box-shadow 0.3s ease;
    }

    tbody tr:hover {
        background: rgba(255, 255, 255, 0.2);
        box-shadow: 0 5px 10px rgba(0, 0, 0, 0.3);
    }

    tbody td {
        padding: 10px 15px;
        color: #e4e4e4;
    }

    /* Стили для активного и неактивного статуса */
    .status {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }

    .status.active {
        background-color: #4caf50; /* Зеленый */
    }

    .status.inactive {
        background-color: #f44336; /* Красный */
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
    </div>
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

                        const lastActiveDate = new Date(item.last_active);
                        const formattedDate = lastActiveDate.toLocaleString();

                        let statusText = item.active ? `Active` : `Inactive | Last active: ${formattedDate}`;

                        row.innerHTML = `
                            <td>${item.nickname}</td>
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

@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE

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
        unique_identifier = deviceid if deviceid != '-' else ip

        cur.execute("""
        INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, allowed, real_nickname, unique_identifier)
        VALUES (%s, %s, %s, %s, %s, %s, FALSE, 'None', %s)
        ON CONFLICT (unique_identifier)
        DO UPDATE SET
            ip = EXCLUDED.ip,
            server = EXCLUDED.server,
            nickname = EXCLUDED.nickname,
            license_active = EXCLUDED.license_active,
            last_active = EXCLUDED.last_active,
            allowed = FALSE,
            real_nickname = COALESCE(user_data.real_nickname, 'None'),
            deviceid = EXCLUDED.deviceid;
        """, (deviceid, ip, server, nickname, license_active, last_active, unique_identifier))

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
        # Выбираем только актуальные записи
        cur.execute("""
        SELECT DISTINCT ON (COALESCE(NULLIF(deviceid, '-'), ip))
               nickname, real_nickname, server, license_active, last_active
        FROM user_data
        ORDER BY COALESCE(NULLIF(deviceid, '-'), ip), last_active DESC;
        """)
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
