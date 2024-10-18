from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import os
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# Длительность активности в секундах
active_duration = timedelta(seconds=30)

# Словарь настоящих никнеймов по IP и их статусам
real_nicknames = {
    "109.72.249.137": ["Mr.Butovsky", True],
    "94.25.173.251": ["Mr.Butovsky_2", True],
    "176.15.170.199": ["Noysi", True],
    # (другие никнеймы)
}

# Функция для подключения к базе данных
def get_db_connection():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Функция для создания таблицы (если её ещё нет)
def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_data (
            id TEXT PRIMARY KEY,
            server TEXT NOT NULL,
            nickname TEXT NOT NULL,
            activated BOOLEAN NOT NULL,
            last_active TIMESTAMP
        );
    ''')
    conn.commit()
    cur.close()
    conn.close()

create_table()

# Функция для сохранения данных пользователя в базу данных
def save_user_data(ip, server, nickname, activated):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO user_data (id, server, nickname, activated, last_active)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE 
        SET server = EXCLUDED.server, 
            nickname = EXCLUDED.nickname, 
            activated = EXCLUDED.activated,
            last_active = EXCLUDED.last_active;
    ''', (ip, server, nickname, activated, datetime.now()))
    conn.commit()
    cur.close()
    conn.close()

# Функция для загрузки данных пользователя
def load_user_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, server, nickname, activated, last_active FROM user_data')
    rows = cur.fetchall()
    user_data = {row[0]: (row[1], row[2], row[3], row[4]) for row in rows}
    cur.close()
    conn.close()
    return user_data

# HTML-шаблон остаётся неизменным
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Полученные данные</title>
    <style>
        /* стили */
    </style>
    <script>
        /* скрипты */
    </script>
</head>
<body>
    <h1>Полученные данные</h1>
    <table>
        <thead>
            <tr>
                <th>IP-адрес</th>
                <th>Сервер</th>
                <th>Никнейм</th>
                <th>Настоящий никнейм</th>
                <th>Статус</th>
                <th>Лицензия</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody id="data-table-body">
            <tr><td colspan="6">Нет данных.</td></tr>
        </tbody>
    </table>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_data(as_text=True)
    if data:
        ip, server, nickname, activated = data.split(" ", 3)
        save_user_data(ip, server, nickname, activated == "True")
    return jsonify({"status": "success", "data": data}), 201

@app.route('/data', methods=['GET'])
def get_data():
    user_data = load_user_data()
    current_time = datetime.now()
    response_data = []
    for ip, (server, nickname, activated, last_active) in user_data.items():
        real_nickname = real_nicknames.get(ip, ["Неизвестно", False])
        status = (current_time - last_active) < active_duration
        license_status = "Активирована" if activated else "Недействительна"
        response_data.append([ip, server, nickname, real_nickname[0], status, license_status])
    return jsonify(response_data)

@app.route('/check_ip/<ip_address>', methods=['GET'])
def check_ip(ip_address):
    if ip_address in real_nicknames:
        user_status = real_nicknames[ip_address][1]
        return str(1 if user_status else 0), 200
    return "0", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
