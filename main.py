from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)

# Глобальный словарь для хранения данных пользователей
user_data = {}
# Длительность активности в секундах
active_duration = timedelta(seconds=30)

# Словарь для настоящих никнеймов по IP и их статусам
real_nicknames = {
    "109.72.249.137": ["Mr.Butovsky", True],
    "176.15.170.199": ["Noysi", True],
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


# Функция для сохранения данных в файл
def save_data_to_file():
    with open(DATA_FILE, 'w') as file:
        # Преобразуем объект datetime в строку для сохранения
        json.dump(
            {
                ip: [server, nickname, activated,
                     last_active.isoformat()]
                for ip, (server, nickname, activated,
                         last_active) in user_data.items()
            }, file)


# Функция для загрузки данных из файла
def load_data_from_file():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as file:
            saved_data = json.load(file)
            for ip, (server, nickname, activated,
                     last_active) in saved_data.items():
                # Преобразуем строку в объект datetime при восстановлении данных
                user_data[ip] = (server, nickname, activated,
                                 datetime.fromisoformat(last_active))


# HTML-шаблон для отображения данных
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
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1 {
            color: #007BFF;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #007BFF;
            color: white;
        }
        .active {
            color: green;
        }
        .inactive {
            color: gray;
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
                        tableBody.innerHTML = '<tr><td colspan="6">Нет данных.</td></tr>'; // Сообщение, если данных нет
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
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                })
                .catch(error => console.error('Ошибка при получении данных:', error));
        }

        // Запускаем обновление каждые 2 секунды
        setInterval(fetchData, 2000);
        // Первоначальный вызов функции для загрузки данных при открытии страницы
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
            </tr>
        </thead>
        <tbody id="data-table-body">
            <tr><td colspan="6">Нет данных.</td></tr>
        </tbody>
    </table>
</body>
</html>
"""


# Обработка GET-запроса
@app.route('/', methods=['GET'])
def home():
    return HTML_TEMPLATE  # Возвращаем HTML-шаблон


# Обработка POST-запроса
@app.route('/data', methods=['POST'])
def receive_data():
    data = request.get_data(as_text=True)  # Получаем данные запроса как текст
    print(f"Получен POST-запрос (необработанные данные): {data}"
          )  # Логируем данные
    if data:  # Проверяем, что данные не пустые
        # Извлекаем ip, server, nickname и activated
        ip, server, nickname, activated = data.split(" ", 3)
        # Обновляем данные пользователя и текущее время
        user_data[ip] = (server, nickname, activated, datetime.now())
        save_data_to_file()  # Сохраняем данные в файл
    return jsonify({
        "status": "success",
        "data": data
    }), 201  # Возвращаем ответ в формате JSON


# Обработка GET-запроса для получения данных
@app.route('/data', methods=['GET'])
def get_data():
    current_time = datetime.now()
    response_data = []
    for ip, (server, nickname, activated, last_active) in user_data.items():
        # Получаем настоящий никнейм по IP
        real_nickname = real_nicknames.get(ip, ["Неизвестно", False])
        # Проверяем, является ли пользователь активным
        status = (current_time - last_active) < active_duration
        # Определяем статус лицензии
        license_status = "Активирована" if activated == "True" else "Недействительна"
        response_data.append(
            [ip, server, nickname, real_nickname[0], status,
             license_status])  # Добавляем данные в список
    return jsonify(response_data)  # Возвращаем данные в формате JSON


# Обработка GET-запроса для проверки активности по IP
@app.route('/check_ip/<ip_address>', methods=['GET'])
def check_ip(ip_address):
    print(f"Запрос на проверку IP: {ip_address}")  # Логирование IP-адреса
    if ip_address in real_nicknames:
        user_status = real_nicknames[ip_address][1]
        return str(1 if user_status else 0), 200
    else:
        return "0", 200



if __name__ == '__main__':
    load_data_from_file()  # Восстанавливаем данные из файла при запуске
    app.run(host='0.0.0.0', port=8080, debug=True)  # Включаем отладочный режим
