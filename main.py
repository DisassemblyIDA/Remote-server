from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import psycopg2
import os

app = Flask(__name__)

# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности в секундах
active_duration = timedelta(seconds=30) 

# Словарь настоящих никнеймов по IP и их статусам
real_nicknames = {
    "109.72.249.137": ["Mr.Butovsky", True],
    "94.25.173.251": ["Mr.Butovsky_2", True],
    "176.15.170.199": ["Noysi", True],
    "176.15.170.1": ["Noysi_2", True],
    "176.15.170.18": ["Noysi_3", True],
    "85.140.18.73": ["Magnus", True],
    "176.192.161.123": ["Praice", True],
    "193.0.155.136": ["Kointo", True],
    "185.153.47.45": ["Spid4", True],
    "178.126.31.239": ["Terakomari", True],
    "90.151.151.119": ["Magnus2", True],
    "37.195.181.198": ["Demfy", True],
    "122.166.86.148": ["Redflame Irido", True],
    "116.75.72.13": ["Redflame Irido", True],
    "176.59.215.218": ["Title", True],
    "24.203.151.174": ["Tahmid", True]
}

# HTML-шаблон с темной темой и кнопками копирования
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Полученные данные</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            color: #333;
            padding: 20px;
        }

        h1 {
            color: #007BFF;
            text-align: center;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }

        th, td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
            text-align: left;
        }

        th {
            background-color: #007BFF;
            color: #fff;
        }

        tr:hover {
            background-color: #f1f1f1;
        }

        .active {
            color: #28a745;
        }

        .inactive {
            color: #dc3545;
        }

        .copy-button {
            background-color: #007BFF;
            color: white;
            border: none;
            padding: 8px 12px;
            cursor: pointer;
            border-radius: 4px;
            transition: background-color 0.3s ease;
        }

        .copy-button:hover {
            background-color: #0056b3;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
    </style>
    <script>
        // Функция для обновления данных
        function fetchData() {
            fetch('/data')
                .then(response => response.json())
                .then(data => {
                    const tableBody = document.getElementById('data-table-body');
                    tableBody.innerHTML = ''; // Очищаем текущие данные
                    if (data.length === 0) {
                        tableBody.innerHTML = '<tr><td colspan="6">Нет данных.</td></tr>';
                    } else {
                        data.forEach(item => {
                            const row = document.createElement('tr');
                            const statusClass = item[4] ? 'active' : 'inactive';
                            row.innerHTML = `
                                <td>${item[0]}</td>
                                <td>${item[1]}</td>
                                <td>${item[2]}</td>
                                <td>${item[3]}</td>
                                <td class="${statusClass}">&#11044;</td>
                                <td>${item[5]}</td>
                                <td><button class="copy-button" onclick="copyToClipboard('${item[0]}')">Копировать IP</button></td>
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                })
                .catch(error => console.error('Ошибка при получении данных:', error));
        }

        // Копирование в буфер обмена
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('Скопировано в буфер обмена: ' + text);
            });
        }

        setInterval(fetchData, 2000);
        window.onload = fetchData;
    </script>
</head>
<body>
    <div class="container">
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
    </div>
</body>
</html>
"""

# Создание таблицы, если не существует
def create_table():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id TEXT PRIMARY KEY,
            server TEXT NOT NULL,
            nickname TEXT NOT NULL,
            activated BOOLEAN NOT NULL,
            last_active TIMESTAMP
        );
    """)
    conn.commit()

create_table()

@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE

@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_data(as_text=True)
    if data:
        ip, server, nickname, activated = data.split(" ", 3)
        last_active = datetime.now()

        # Сохранение данных в БД
        cur.execute("""
            INSERT INTO user_data (id, server, nickname, activated, last_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
            server = EXCLUDED.server,
            nickname = EXCLUDED.nickname,
            activated = EXCLUDED.activated,
            last_active = EXCLUDED.last_active;
        """, (ip, server, nickname, activated == 'True', last_active))
        conn.commit()
    
    return jsonify({"status": "success", "data": data}), 201

@app.route('/update_activity', methods=['POST'])
def update_activity():
    # Получение IP-адреса пользователя (например, из заголовков или данных запроса)
    ip = request.remote_addr
    
    # Обновление времени последней активности пользователя в базе данных
    current_time = datetime.now()  # Текущее время
    cur.execute("UPDATE user_data SET last_active = %s WHERE ip = %s", (current_time, ip))
    conn.commit()  # Сохраняем изменения в базе данных
    
    return "Activity updated", 200


@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now()  # Получаем текущее время
    cur.execute("SELECT * FROM user_data;")
    users = cur.fetchall()

    response_data = []
    for ip, server, nickname, activated, last_active in users:
        real_nickname = real_nicknames.get(ip, ["Неизвестно", False])
        
        # Преобразуем last_active в datetime, если он является строкой или другим типом
        if isinstance(last_active, datetime):
            time_diff = current_time - last_active
            status = time_diff < active_duration  # Проверяем, прошло ли больше 30 секунд
        else:
            status = False  # Если last_active не определен, пользователь не активен
        
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
