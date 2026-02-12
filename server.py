import asyncio
from datetime import datetime
import ssl
from user_auth import register_user, authenticate_user, get_nickname
from rules import login_check, password_check, nickname_check
from messages import save_message, messages_history


# Объявляем IP-адрес и порт на котором будет работать сервер.
HOST = '127.0.0.1'
PORT = 9090

# Создаем список клиентов, объявляем экземпляр класса Lock для предотвращения конфликтов при множественном доступе к словарю.
# Объявлем множество для хранения задач клиентов, чтобы впоследствии их корректно завершать через цикл.
clients = {}
clients_lock  = asyncio.Lock()
clients_tasks = set()

async def server_commands(server):
    '''Функция для обработки команд сервера. В данный момент доступны две команды - /shutdown и /list.
    Первая команда завершает работу сервера, последовательно отключая всех клиентов и завершая их задачи.
    Вторая команда выводит список подключенных клиентов.
    '''

    loop = asyncio.get_running_loop()
    while True:
        command = await loop.run_in_executor(None, input)
        if command == '/shutdown':
            # Делаем блокировку, создаем список из значений словаря и потом его очищаем. Затем проходим по всем клиентам и отправляем им сообщение о завершении работы.
            async with clients_lock:
                targets = list(clients.values())
                clients.clear()
            for clnt in targets:
                try:
                    clnt.write('Сервер принудительно завершает работу.\n'.encode())
                    await clnt.drain()
                    clnt.write('__server_shutdown__\n'.encode())
                    await clnt.drain()
                    clnt.close()
                except Exception:
                    pass
            
            print('Closing clients tasks...')
            for task in list(clients_tasks):
                task.cancel()
            await asyncio.gather(*clients_tasks, return_exceptions=True)
            
            print('Server shutting down...')
            server.close()
            await server.wait_closed()
            break

        elif command == '/list':
            print(f'Количество клиентов онлайн: {len(clients)}')
            print(f'Список клиентов: [{', '.join(clients.keys())}]')
        else:
            print('Unknown command')


async def entrance(writer, reader):
    '''Функция с циклом ожидания команд от пользователя, в зависимости от его выбора выполняется одно из 3-х действий:
    1. Регистрация нового пользователя.
    2. Авторизация пользователя.
    3. Выход из программы.
    '''

    while True: 
        writer.write('Введите команду для регистрации [registration], входа [login] или выхода [quit]:\n'.encode())
        await writer.drain()

        user_choice = (await reader.readline()).decode().strip()
        
        if user_choice == '__registration__':
            user_login = (await reader.readline()).decode().strip()

            result, text = login_check(user_login)
            if not result: # Проверка логина на соответствие требованиям
                if text == 'length_error':
                    writer.write('__length_error__\n'.encode())
                    await writer.drain()
                else:
                    writer.write('__format_error__\n'.encode())
                    await writer.drain()
                continue
            else:
                writer.write('__login_ok__\n'.encode())
                await writer.drain()

            user_password = (await reader.readline()).decode().strip()        

            result, text = password_check(user_password)
            if not result: # Проверка пароля на соответствие требованиям
                if text == 'length_error':
                    writer.write('__length_error__\n'.encode())
                    await writer.drain()
                else:
                    writer.write('__format_error__\n'.encode())
                    await writer.drain()
                continue
            else:
                writer.write('__password_ok__\n'.encode())
                await writer.drain()
            
            nickname = (await reader.readline()).decode().strip()

            result, text = nickname_check(nickname)
            if not result: # Проверка пароля на соответствие требованиям
                if text == 'length_error':
                    writer.write('__length_error__\n'.encode())
                    await writer.drain()
                else:
                    writer.write('__format_error__\n'.encode())
                    await writer.drain()
                continue
            else:
                writer.write('__nickname_ok__\n'.encode())
                await writer.drain()
            
            success, text = register_user(user_login, user_password, nickname)

            if success:
                writer.write('__registration_success__\n'.encode())
                await writer.drain()
                continue
            else:
                if text == 'username_exists':
                    writer.write('__username_exists__\n'.encode())
                    await writer.drain()
                    continue
                elif text == 'nickname_exists':
                    writer.write('__nickname_exists__\n'.encode())
                    await writer.drain()
                    continue
                else:
                    print(f'Registration error: {text}')
                    writer.write('__error__\n'.encode())
                    await writer.drain()
                    continue
                
        elif user_choice == '__login__':
            user_login = (await reader.readline()).decode().strip()

            user_password = (await reader.readline()).decode().strip()
            
            success, text = authenticate_user(user_login, user_password)

            if success:
                result, nickname = get_nickname(user_login)
                if result:
                    writer.write('__login_success__\n'.encode())
                    await writer.drain()
                    return True, nickname
                else:
                    writer.write('__nickname_error__\n'.encode())
                    await writer.drain()
                    continue
            else:
                if text in ('no_user, bad_password'):
                    writer.write('__bad_data__\n'.encode())
                    await writer.drain()
                    continue
                else:
                    print(f'Authentication error: {text}')
                    writer.write('__error__\n'.encode())
                    await writer.drain()
                    continue
        elif user_choice == '__repeat__':
            continue  
        else:
            return False, None


async def user_msg_broadcast(client, nickname, text):
    '''Функция для отправки сообщений всем клиентам. Принимает клиента, его никнейм и текст сообщения.
    Через цикл проходимся по всем клиентам, кроме того, который отправил сообщение и отправляем текст сообщения.
    После отправки сохраняем сообщение в базе данных.
    '''

    message = f'{datetime.now().strftime("%H:%M")} [{nickname}]: {text}'
    for clnt in clients.values():
        if clnt != client:
            clnt.write((message + '\n').encode())
            await clnt.drain()
    success, text_result = save_message(nickname, text)
    if not success:
        print(text_result)


async def system_broadcast(client, nickname, text):
    '''Функция системных оповещений. Оповещает всех если клиент зашел или вышел из чата.'''
    
    message = f'[!]Системное оповещение: Пользователь {nickname} {text}.'
    for clnt in clients.values():
        if clnt != client:
            clnt.write((message + '\n').encode())
            await clnt.drain()


async def handle_client(reader, writer):
    '''Фунция принятия и обработки клиентов. При каждом новом подключении создается задача.
    При подключении клиента запускается функция аутентификации(entrance).
    После успешной аутентификации отправляем клиенту историю сообщений.
    Дальше бесконечный цикл ожидания сообщения от клиента.
    '''
    task = asyncio.current_task()
    clients_tasks.add(task)
    
    # Получаем IP-адрес и порт клиента
    addr = writer.get_extra_info('peername')
    print(f'Client {addr} connected')
    
    try:
        writer.write('Вы подключились к серверу!\n'.encode())
        await writer.drain()
        
        # Если функция входа возвращает True, то клиент аутентифицирован в ином случае(пользователь не захотел войти в чат)
        # переходим к блоку finally, где закрываем соединение.
        result, nickname = await entrance(writer, reader)
        if result:
            writer.write(f'Ваш никнейм: {nickname}\n'.encode())
            await writer.drain()

            success, history = messages_history() # Получаем историю сообщений
            if success:
                writer.write((str(len(history)) + '\n').encode()) # Отправляем количество сообщений, чтобы клиент знал сколько принимать
                await writer.drain()

                for hist_nickname, hist_msg, hist_time in reversed(history): # Отправляем историю сообщений
                    writer.write(f'({hist_time} {hist_nickname}): {hist_msg}\n'.encode())
                    await writer.drain()
            else:
                print(history)
            
            async with clients_lock: # Добавляем никнейм клиента в словарь
                clients[nickname] = writer
            await system_broadcast(writer, nickname, 'вошел в чат') # Оповещаем всех о входе нового клиента

            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break
                    msg = data.decode().strip()

                    # Пользователь может захотеть сам отключиться, в таком случае в клиенте реализована команда /exit(смотри код клиента).
                    # При таком отключении происходит отправка всем, что пользователь вышел из чата.
                    # После этого удаляет клиента из словаря и закрывает его соединение.

                    if msg == '__disconnect__': 
                        await system_broadcast(writer, nickname, 'вышел из чата')
                        async with clients_lock:
                            del clients[nickname]
                        break
                    # Отправляем сообщения клиента всем.
                    await user_msg_broadcast(writer, nickname, msg)
                except asyncio.CancelledError:
                    break
    except Exception as e:
        print(f'Error occured: {e}')       
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        clients_tasks.discard(task)
        print(f'Client {addr} disconnected')
        

async def main():
    '''Основная функция. 
    Загружается SSL сертификат и ключ, после чего ожидание входящих соединений.
    Запускается функция обработки команд сервер.
    Сервер работает бесконечно, пока не будет введена команда /shutdown.
    '''
    
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(certfile='server.crt', keyfile='server.key')
    server = await asyncio.start_server(handle_client, HOST, PORT, ssl=ssl_ctx)
    print('Server started. Available commands: /list, /shutdown')
    cmd_task = asyncio.create_task(server_commands(server))
    await cmd_task
    print('Server stopped')

asyncio.run(main())