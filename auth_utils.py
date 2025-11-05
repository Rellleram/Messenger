import bcrypt

#Функция хеширования пароля с помощью bcrypt. Возвращает хешированный пароль.
def hash_password(password):
    password_bytes = password.encode()
    salt = bcrypt.gensalt()

    hashed_password = bcrypt.hashpw(password_bytes, salt).decode()

    return hashed_password

#Функция проверки совпадения пароля введенного пользователем с хэшом в базе данных. Возвращает True или False.
def verify_password(password, hashed_password):
    password_bytes = password.encode()

    hashed_bytes = hashed_password.encode()

    return bcrypt.checkpw(password_bytes, hashed_bytes)