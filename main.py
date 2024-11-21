from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta, timezone  # Добавлен timezone
import psycopg2
import os

app = Flask(__name__)
#
# Подключение к PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cur = conn.cursor()

# Длительность активности в секундах
active_duration = timedelta(seconds=30)

# Словарь настоящих никнеймов по IP и их статусам
real_nicknames = {
    "109.72.249.137": ["Mr.Butovsky", True],
    "94.25.173.251": ["Mr.Butovsky", True],
    "94.25.175.132": ["Mr.Butovsky", True],
    "94.25.174.119": ["Mr.Butovsky", True],
    "94.25.174.96": ["Mr.Butovsky", True],
    "176.15.170.199": ["Noysi", True],
    "176.15.170.1": ["Noysi", True],
    "176.15.170.18": ["Noysi", True],
    "176.15.170.17": ["Noysi", True],
    "176.15.170.138": ["Noysi", True],
     "176.15.170.182": ["Noysi", True],
    "193.0.155.136": ["Kointo", True],
    "178.126.224.165": ["Zeref", True],
    "178.126.31.239": ["Terakomari", True],
    "2.63.255.157": ["Manje", True],
    "37.195.181.198": ["Demfy", True],
    "122.166.86.148": ["Redflame Irido", True],
    "116.75.72.13": ["Redflame Irido", True],
    "176.59.215.218": ["Title", True],
    "24.203.151.174": ["Tahmid", True],
    "178.126.155.181": ["Zeref", True],
    "178.126.144.108": ["Zeref", True],
    "94.25.171.227": ["Mr.Butovsky", True],
    "178.126.3.46": ["Zeref", True],
    "31.162.228.195": ["Magnus", True],
    "176.15.170.139": ["Noysi", True],
    "176.15.170.188": ["Noysi", True],
    "176.15.170.177": ["Noysi", True],
    "116.72.73.15": ["Redflame Irido", True],
    "95.220.27.219": ["Praice", True],
    "185.253.180.24": ["Noysi", True],
    "176.15.170.172": ["Noysi", True],
    "94.25.173.49": ["Mr.Butovsky", True], 
    "27.4.53.14": ["Redflame Irido", True],
    "176.15.170.12": ["Noysi", True],
    "94.51.15.179": ["Magnus", True],
    "178.126.209.193": ["Zeref", True],
    "176.15.170.174": ["Noysi", True],
    "188.17.212.184": ["Magnus", True],
    "94.51.17.225": ["Magnus", True]
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
   
    
    

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
                        tableBody.innerHTML = '<tr><td colspan="7">Нет данных.</td></tr>';
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
                <tr><td colspan="7">Нет данных.</td></tr>
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
    print(f"Получены данные: {data}")  # Логирование полученных данных
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

@app.route('/data', methods=['GET'])
def get_data():
    print("Получена какая-то дата")
    
    # Получаем текущее время с учетом часового пояса
    current_time = datetime.now(timezone.utc)
    
    cur.execute("SELECT * FROM user_data;")
    users = cur.fetchall()

    response_data = []
    for ip, server, nickname, activated, last_active in users:
        real_nickname = real_nicknames.get(ip, ["Неизвестно", False])
        
        # Проверка, что last_active действительно является datetime
        if isinstance(last_active, datetime):
            # Приводим last_active к UTC, если оно не aware
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
                
            time_diff = current_time - last_active
            status = time_diff < active_duration  # Проверяем, прошло ли больше 30 секунд
            print("status:", status)
        else:
            status = False  # Если last_active не определен, пользователь не активен
            print("last_active не определен")
        
        # Лицензия
        license_status = "Активирована" if activated else "Недействительна"
        
        # Отправка данных для фронтенда
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
