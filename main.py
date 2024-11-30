@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_json()
    deviceid = data.get("deviceid")
    ip = data.get("ip")
    server = data.get("server")
    nickname = data.get("nickname")
    license_active = data.get("license_status") == "activated"
    last_active = datetime.now(timezone.utc)

    if not ip:
        return jsonify({"error": "ip is required"}), 400

    try:
        if deviceid == "-":
            # Если deviceid временный, обновляем или добавляем запись по IP
            cur.execute("""
                INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ip) DO UPDATE
                SET deviceid = EXCLUDED.deviceid,
                    server = EXCLUDED.server,
                    nickname = EXCLUDED.nickname,
                    license_active = EXCLUDED.license_active,
                    last_active = EXCLUDED.last_active;
            """, (deviceid, ip, server, nickname, license_active, last_active, False))
        else:
            # Если deviceid уникальный, обновляем или добавляем запись по deviceid
            cur.execute("""
                INSERT INTO user_data (deviceid, ip, server, nickname, license_active, last_active, allowed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (deviceid) DO UPDATE
                SET ip = EXCLUDED.ip,
                    server = EXCLUDED.server,
                    nickname = EXCLUDED.nickname,
                    license_active = EXCLUDED.license_active,
                    last_active = EXCLUDED.last_active;
            """, (deviceid, ip, server, nickname, license_active, last_active, False))

        conn.commit()
        return jsonify({"status": "success"}), 201

    except psycopg2.Error as e:
        conn.rollback()
        print("Error occurred while receiving data:", e)
        return jsonify({"error": "Internal server error"}), 500
