import sqlite3
from datetime import datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))

DB_PATH = 'messenger.db'

def connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

'''Функция соохранения сообщений в БД. Сохраянется никнейм, текст и текущее время по МСК
После сохранения проверяется сколько сообщений на данный момент в БД.
Если сообщений больше 100 удаляем старые'''
def save_message(nickname, text):
    conn = connection()
    cur = conn.cursor()

    now_msk = datetime.now(MSK).strftime('%d.%m %H:%M')

    try:
        cur.execute("INSERT INTO messages (nickname, text, created_at) VALUES (?, ?, ?)", 
                    (nickname, text, now_msk))

        
        cur.execute("SELECT COUNT(*) FROM messages")
        count = cur.fetchone()[0]

        if count > 100:
            quantity = count - 100
            cur.execute("DELETE FROM messages WHERE id IN (SELECT id FROM messages ORDER BY id ASC LIMIT ?)",
                        (quantity,))
        conn.commit()
        return True, 'saved'
    
    except Exception as e:
        return False, f'Error: {e}'
    
    finally:
        conn.close()
    
'''Функция получения последних 100 сообщений из БД'''
def messages_history():
    conn = connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT nickname, text, created_at FROM messages ORDER BY id DESC LIMIT 100')
        messages = cur.fetchall()
        return True, messages
    
    except Exception as e:
        return False, f'Error: {e}'
    finally:
        conn.close()
        