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

    # Пропуск записи, если deviceid равен "-"
    if not deviceid or deviceid == "-":
        return jsonify({"error": "Invalid deviceid"}), 400

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

@app.route('/check_ip/<deviceid>', methods=['GET'])
def check_ip(deviceid):
    if not deviceid or deviceid == "-":
        return "0"  # Неверный deviceid считается отсутствующим
    cur.execute("SELECT 1 FROM user_data WHERE deviceid = %s LIMIT 1;", (deviceid,))
    exists = cur.fetchone() is not None
    return "1" if exists else "0"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
