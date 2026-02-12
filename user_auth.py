import sqlite3
from auth_utils import hash_password, verify_password


DB_PATH = 'messenger.db'


def connection():
    '''Функци возвращает подключение к БД.'''
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def register_user(username, password, nickname):
    '''Функция регистрации пользователя. 
    Возвращает True, если регистрация успешна и False, если такой логин уже существует.
    '''

    conn = connection()
    cur = conn.cursor()

    try:
        password_hash = hash_password(password)

        cur.execute("INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)", (username, password_hash, nickname))

        conn.commit()
        return True, 'registered'
     
    except sqlite3.IntegrityError as e:
        if 'username' in str(e):
            return False, 'username_exists'
        elif 'nickname' in str(e):
            return False, 'nickname_exists'
        else:
            return False, f'integrity_error: {e}'
    except Exception as e:
        return False, f'error: {e}'
    finally:
        conn.close()


def authenticate_user(username, password):
    '''Функция аутентификации. Проверяет логин и пароль. 
    Возвращает True, если пароль верен и False, если пользователя не существует или пароль неверен.
    '''

    conn = connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT password FROM users WHERE  username = ?', (username, ))

        row = cur.fetchone()
        if not row:
            return False, 'no_user'
        password_hash = row[0]
        if verify_password(password, password_hash):
            return True, 'ok'
        else:
            return False, 'bad_password'
    except Exception as e:
        return False, f'error: {e}'
    finally:
        conn.close()

def get_nickname(username):
    '''Функция возвращает никнейм пользователя по логину.'''

    conn = connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT nickname FROM users WHERE  username = ?', (username, ))

        row = cur.fetchone()
        return True, row[0]
    except Exception as e:
        return False, f'error: {e}'
    finally:
        conn.close()