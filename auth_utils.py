import bcrypt


def hash_password(password):
    '''Функция хеширования пароля с помощью bcrypt. Возвращает хешированный пароль.'''
    
    password_bytes = password.encode()
    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt).decode()

    return hashed_password


def verify_password(password, hashed_password):
    '''Функция проверки совпадения пароля введенного пользователем с хэшом в базе данных. Возвращает True или False.'''

    password_bytes = password.encode()

    hashed_bytes = hashed_password.encode()

    return bcrypt.checkpw(password_bytes, hashed_bytes)