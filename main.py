from flask import Flask, request, jsonify
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
        -- Устанавливаем unique_identifier только при вставке
        IF TG_OP = 'INSERT' THEN
            NEW.unique_identifier = CASE
                WHEN NEW.deviceid = '-' THEN NEW.ip
                ELSE NEW.deviceid
            END;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS update_unique_identifier_trigger ON user_data;
    CREATE TRIGGER update_unique_identifier_trigger
    BEFORE INSERT ON user_data
    FOR EACH ROW EXECUTE FUNCTION update_unique_identifier();
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
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    if not ip:
        return jsonify({"error": "IP is required"}), 400

    try:
        # Проверяем, существует ли строка с таким deviceid или ip
        cur.execute("""
            SELECT deviceid FROM user_data
            WHERE unique_identifier = %s OR unique_identifier = %s;
        """, (deviceid, ip))
        existing = cur.fetchone()

        if existing:
            # Обновляем существующую запись
            cur.execute("""
                UPDATE user_data
                SET ip = %s,
                    server = %s,
                    nickname = %s,
                    license_active = %s,
                    last_active = %s,
                    deviceid = %s
                WHERE unique_identifier = %s OR unique_identifier = %s;
            """, (ip, server, nickname, license_active, last_active, deviceid, deviceid, ip))
        else:
            # Вставляем новую запись
            cur.execute("""
                INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (deviceid, ip, server, nickname, license_active, last_active, False))

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
