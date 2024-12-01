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

# Создание таблицы, если не существует
def setup_database():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_data (
        deviceid TEXT PRIMARY KEY,
        ip TEXT NOT NULL,
        server TEXT NOT NULL,
        nickname TEXT NOT NULL,
        last_active TIMESTAMP NOT NULL,
        allowed BOOLEAN DEFAULT FALSE
    );
    """)
    conn.commit()

setup_database()

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    deviceid = data.get("deviceid", "-")
    ip = data.get("ip")
    server = data.get("server", "unknown")
    nickname = data.get("nickname", "unknown")
    last_active = datetime.now(timezone.utc)

    if not ip:
        return jsonify({"error": "IP is required"}), 400

    if deviceid == "-":
        return jsonify({"status": "ignored"}), 200

    try:
        cur.execute("""
        INSERT INTO user_data (deviceid, ip, server, nickname, last_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (deviceid)
        DO UPDATE SET
            ip = EXCLUDED.ip,
            server = EXCLUDED.server,
            nickname = EXCLUDED.nickname,
            last_active = EXCLUDED.last_active;
        """, (deviceid, ip, server, nickname, last_active))

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
        cur.execute("""
        SELECT nickname, server, allowed, last_active
        FROM user_data;
        """)
        rows = cur.fetchall()

        response = []
        for nickname, server, allowed, last_active in rows:
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
            active = (current_time - last_active) < ACTIVE_DURATION
            response.append({
                "nickname": nickname,
                "server": server,
                "license_status": "Active" if allowed else "Inactive",
                "status": "Now" if active else last_active.isoformat()
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
