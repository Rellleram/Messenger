import sqlite3
import os


conn = sqlite3.connect('messenger.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    nickname TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT,
    text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

conn.commit()
print('======Проверка базы данных======')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Таблицы в БД:", tables)

# Проверяем файл
if os.path.exists('messenger.db'):
    size = os.path.getsize('messenger.db')
    print(f"Файл: messenger.db")
    print(f"Размер: {size} байт")
    print(f"Путь: {os.path.abspath('messenger.db')}")
else:
    print("Файл БД не найден!")
conn.close()

