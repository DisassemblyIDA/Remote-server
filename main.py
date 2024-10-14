from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# Глобальный словарь для хранения данных пользователей
user_data = {}
# Длительность активности в секундах
active_duration = timedelta(seconds=30)

# Словарь настоящих никнеймов по IP и их статусам
real_nicknames = {
    "109.72.249.137": ["Mr.Butovsky", True],
    "94.25.173.251": ["Mr.Butovsky2", True],
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
    "176.59.215.218": ["Titl", True]
}
DATA_FILE = 'user_data.json'


def save_data_to_file():
    """Сохранение данных в файл (чистая функция)."""
    with open(DATA_FILE, 'w') as file:
        json.dump(
            {ip: [server, nickname, activated, last_active.isoformat()]
             for ip, (server, nickname, activated, last_active) in user_data.items()},
            file
        )


def load_data_from_file():
    """Загрузка данных из файла (чистая функция)."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            saved_data = json.load(file)
            for ip, (server, nickname, activated, last_active) in saved_data.items():
                user_data[ip] = (server, nickname, activated, datetime.fromisoformat(last_active))


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
            font-family: Arial, sans-serif;
            background-color: #121212;
            color: #f4f4f4;
            padding: 20px;
        }
        h1 {
            color: #007BFF;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        th, td {
            border: 1px solid #333;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #007BFF;
            color: white;
        }
        .active {
            color: #4CAF50;
        }
        .inactive {
            color: gray;
        }
        .copy-button {
            background-color: #007BFF;
            color: white;
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 4px;
        }
        .copy-button:hover {
            background-color: #0056b3;
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
        user_data[ip] = (server, nickname, activated, datetime.now())
        save_data_to_file()
    return jsonify({"status": "success", "data": data}), 201


@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now()
    response_data = []
    for ip, (server, nickname, activated, last_active) in user_data.items():
        real_nickname = real_nicknames.get(ip, ["Неизвестно", False])
        status = (current_time - last_active) < active_duration
        license_status = "Активирована" if activated == "True" else "Недействительна"
        response_data.append([ip, server, nickname, real_nickname[0], status, license_status])
    return jsonify(response_data)


@app.route('/check_ip/<ip_address>', methods=['GET'])
def check_ip(ip_address):
    if ip_address in real_nicknames:
        user_status = real_nicknames[ip_address][1]
        return str(1 if user_status else 0), 200
    return "0", 200


if __name__ == '__main__':
    load_data_from_file()
    app.run(host='0.0.0.0', port=8080, debug=True)
