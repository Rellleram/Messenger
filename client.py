import asyncio
import ssl
from rules import rules_login, rules_password, rules_nickname


# Объявляем IP-адрес и порт по которым клиент будет подключаться к серверу.
HOST = '127.0.0.1'
PORT = 9090


async def authenticate(writer, reader):
    '''Функция для обработки команд клиента. Доступны 3 команды:
    1. registration - регистрация, если пользователь новый.
    2. login - авторизация пользователя.
    3. quit - выход из программы.
    '''

    print((await reader.readline()).decode().strip()) # Вывод сообщения о подключении к серверу
    loop = asyncio.get_running_loop()
    while True:
        print((await reader.readline()).decode().strip()) # Вывод доступных команд
        choice = await loop.run_in_executor(None, input)
        
        if choice == 'registration':
            writer.write('__registration__\n'.encode())
            await writer.drain()
            
            print(rules_login()) # Вывод правил для логина
            print((await reader.readline()).decode().strip()) # 'Введите логин'
            login = await loop.run_in_executor(None, input)
            writer.write((login + '\n').encode())
            await writer.drain()

            log_answer = (await reader.readline()).decode().strip()
            if log_answer == '__login_error__':
                print('Логин не соответствует требованиям. Попробуйте еще раз.')
                continue
            
            print(rules_password()) # Вывод правил для пароля
            print((await reader.readline()).decode().strip()) # 'Введите пароль'
            password = await loop.run_in_executor(None, input)
            writer.write((password + '\n').encode())
            await writer.drain()

            pass_answer = (await reader.readline()).decode().strip()
            if pass_answer == '__password_error__':
                print('Пароль не соответствует требованиям. Попробуйте еще раз.')
                continue
            
            print(rules_nickname()) # Вывод правил для никнейма
            print((await reader.readline()).decode().strip()) # 'Введите никнейм'
            nickname = await loop.run_in_executor(None, input)
            writer.write((nickname + '\n').encode())
            await writer.drain()

            nick_answer = (await reader.readline()).decode().strip()
            if nick_answer == '__nickname_error__':
                print('Никнейм не соответствует требованиям. Попробуйте еще раз.')
                continue

            result_answer = (await reader.readline()).decode().strip() # Ответ от сервера о результате регистрации
            if result_answer == '__registration_success__':
                print('Вы успешно зарегистированы!')
                continue
            elif result_answer == '__username_exists__':
                print('Такой логин уже зарегистрирован.')
                continue
            elif result_answer == '__nickname_exists__':
                print('Такой никнейм уже существует.')
                continue
            else:
                print('Произошла ошибка при регистрации. Попробуйте еще раз.')
                continue

        elif choice == 'login':
            writer.write('__login__\n'.encode())
            await writer.drain()
            
            print((await reader.readline()).decode().strip())
            login = await loop.run_in_executor(None, input)
            writer.write((login + '\n').encode())
            await writer.drain()
            
            print((await reader.readline()).decode().strip())
            password = await loop.run_in_executor(None, input)
            writer.write((password + '\n').encode())
            await writer.drain()

            answer = (await reader.readline()).decode().strip()
            if answer == '__login_success__':
                print('Вы успешно вошли в чат!')
                print((await reader.readline()).decode().strip()) # Вывод никнейма

                print('Последние 100 сообщений в чате:')
                history_len = (await reader.readline()).decode().strip() # Количество сообщений в истории
                for _ in range(int(history_len)): # Вывод последних 100 сообщений
                    print((await reader.readline()).decode().strip())
                
                return True
            elif answer == '__nickname_error__':
                print('Ошибка получения никнейма. Попробуйте позже.')
                continue
            elif answer == '__bad_data__':
                print('Неверный логин или пароль.')
                continue
            else:
                print('Произошла ошибка при авторизации. Попробуйте еще раз.')
                continue
        elif choice == 'quit':
            writer.write('__quit__\n'.encode())
            await writer.drain()
            return False
        else:
            print('Неверная команда. Попробуйте еще раз.')
            writer.write('__repeat__\n'.encode())
            await writer.drain()
            continue

    

async def receive_message(reader):
    '''Функция приема сообщений. Бесконечный цикл ожидания сообщений от сервера и их вывода. 
    Если сервер принудительно завершает работу, цикл завершается.
    '''

    while True:
        msg = (await reader.readline()).decode().strip()
        if msg == '__server_shutdown__':
            break
        elif not msg:
            break
        print(msg)


async def send_message(writer):
    '''Функция отправки сообщений. Запускается бесконечный цикл ожидания ввода сообщения пользователем и отправки его серверу.
    Если пользователь вводит /exit, то серверу отправляется сообщение, что клиент отключился и цикл завершается.
    '''

    print('Введите сообщение. Для выхода введите /exit')
    loop = asyncio.get_running_loop()
    while True:
        msg = await loop.run_in_executor(None, input)
        if msg == '/exit':
            writer.write('__disconnect__\n'.encode())
            await writer.drain()
            break
        writer.write((msg + '\n').encode())
        await writer.drain()

async def connection_and_auth():
    '''Функция подключения и аутентификации. Сначала устанавливается TLS-соединение, для безопасного взаимодействия с сервером.
    Затем запускается функция аутентификации. Если аутентификация прошла успешно(вернула True), то запускается функция main.
    '''

    CERT = '''-----BEGIN CERTIFICATE-----
-----END CERTIFICATE-----
'''
    
    ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    ssl_ctx.load_verify_locations(cadata=CERT)
    reader, writer = await asyncio.open_connection(HOST, PORT, ssl=ssl_ctx)
    if await authenticate(writer, reader):
        await main(writer, reader)


async def main(writer, reader):
    '''Функция запуска двух задач с приемом и отправкой сообщений.'''
    rcv_msg = asyncio.create_task(receive_message(reader))
    snd_msg = asyncio.create_task(send_message(writer))
    # Ожидание завершение хотя бы одной из задач. Если одна из них завершилась, то завершается и вторая.
    await asyncio.wait([rcv_msg, snd_msg], return_when=asyncio.FIRST_COMPLETED)
    rcv_msg.cancel()
    snd_msg.cancel()
    writer.close()
    await writer.wait_closed()

asyncio.run(connection_and_auth())

