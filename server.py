import asyncio
from datetime import datetime
import ssl
from user_auth import register_user, authenticate_user

#Объявляем IP-адрес и порт на котором будет работать сервер.
HOST = '127.0.0.1'
PORT = 9090

'''Создаем список клиентов, объявляем экземпляр класса Lock для предотвращения конфликтов при множественном доступе к словарю.
Объявлем множество для хранения задач клиентов, чтобы впоследствии их корректно завершать через цикл.'''
clients = {}
clients_lock  = asyncio.Lock()
clients_tasks = set()

'''Функция для обработки команд сервера. В данный момент доступны две команды - /shutdown и /list.
Первая команда завершает работу сервера, последовательно отключая всех клиентов и завершая их задачи.
Вторая команда выводит список подключенных клиентов.'''
async def server_commands(server):
    loop = asyncio.get_running_loop()
    while True:
        command = await loop.run_in_executor(None, input)
        if command == '/shutdown':
            #Делаем блокировку, создаем список из значений словаря и потом его очищаем. Затем проходим по всем клиентам и отправляем им сообщение о завершении работы.
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

'''Функция с циклом ожидания команд от пользователя, в зависимости от его выбора выполняется одно из 3-х действий:
1. Регистрация нового пользователя
2. Авторизация пользователя
3. Выход из программы'''
async def entrance(writer, reader):
    while True: 
        writer.write('Введите команду для регистрации [registration], входа [login] или выхода [quit]:\n'.encode())
        await writer.drain()

        user_choice = (await reader.readline()).decode().strip()
        
        if user_choice == '__registration__':
            writer.write('Введите логин:\n'.encode())
            await writer.drain()
            user_login = (await reader.readline()).decode().strip()
            
            writer.write('Введите пароль:\n'.encode())
            await writer.drain()
            user_password = (await reader.readline()).decode().strip()
            
            success, text = register_user(user_login, user_password)

            if success:
                writer.write('__registration_success__\n'.encode())
                await writer.drain()
                continue
            else:
                if text == 'username_exists':
                    writer.write('__username_exists__\n'.encode())
                    await writer.drain()
                    continue
                else:
                    print(f'Registration error: {text}')
                    writer.write('__error__\n'.encode())
                    await writer.drain()
                    continue
        elif user_choice == '__login__':
            writer.write('Введите логин:\n'.encode())
            await writer.drain()
            user_login = (await reader.readline()).decode().strip()
            
            writer.write('Введите пароль:\n'.encode())
            await writer.drain()
            user_password = (await reader.readline()).decode().strip()
            
            success, text = authenticate_user(user_login, user_password)

            if success:
                writer.write('__login_success__\n'.encode())
                await writer.drain()
                return True
            else:
                if text == 'bad_password':
                    writer.write('__bad_password__\n'.encode())
                    await writer.drain()
                    continue
                elif text == 'no_user':
                    writer.write('__no_user__\n'.encode())
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
            return False


'''Функция для отправки сообщений всем клиентам. Принимает клиента, его никнейм и текст сообщения.
Через цикл проходимся по всем клиентам, кроме того, который отправил сообщение и отправляем текст сообщения'''
async def broadcast(client, nickname, message):
    for clnt in clients.values():
        if clnt != client:
            clnt.write(f'{datetime.now().strftime("%H:%M")} [{nickname}]: {message}\n'.encode())
            await clnt.drain()

'''Фунция принятия и обработки клиентов. При каждом новом подключении создается задача.
При подключении клиенту отправляется сообщением о том, что он подключился к серверу и предлагается ввести никнейм. Пока клиент не введет никнейм общаться нельзя.
Если никнейм, который клиент ввел уже существует - ему об этом сообщается и он должен ввести другой никнейм.
Дальше бесконечный цикл ожидания сообщения от клиента.'''
async def handle_client(reader, writer):
    task = asyncio.current_task()
    clients_tasks.add(task)
    
    try:
        #Получаем IP-адрес и порт клиента
        addr = writer.get_extra_info('peername')
        print(f'Client {addr} connected')
        writer.write('Вы подключились к серверу!\n'.encode())
        await writer.drain()
        
        #Если функция входа возвращает True, предлагается ввести никнейм, после чего можно общаться 
        #Если функция входа возвращает False, то переходим к блоку finally и отключаем клиента
        if await entrance(writer, reader):
            writer.write('Введите ваш никнейм:\n'.encode())
            await writer.drain()
            nickname = (await reader.readline()).decode().strip()

            async with clients_lock:
                clients[nickname] = writer
            await broadcast(writer, nickname, 'Вошел в чат.')

            while True:
                try:
                    data = await reader.readline()
                    if not data:
                        break
                    msg = data.decode().strip()
                    #Пользователь может захотеть сам отключиться, в таком случае в клиенте реализована команда /exit(смотри код клиента).
                    #При таком отключении сервер всем отправляет, что пользователь вышел из чата, удаляет клиента из словаря и закрывает его соединение.
                    if msg == '__disconnect__':
                        await broadcast(writer, nickname, 'Пользователь вышел из чата.')
                        async with clients_lock:
                            del clients[nickname]
                        break
                    #Отправляем сообщения клиента всем.
                    await broadcast(writer, nickname, msg)
                except asyncio.CancelledError:
                    break
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        clients_tasks.discard(task)
        print(f'Client {addr} disconnected')
        
'''Основная функция. Запускается сервер. Запускается функция принятия и обработки клиентов. Запускается функция обработки команд сервера.
Сервер работает бесконечно, пока не будет введена команда /shutdown'''
async def main():
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(certfile='server.crt', keyfile='server.key')
    server = await asyncio.start_server(handle_client, HOST, PORT, ssl=ssl_ctx)
    print('Server started. Available commands: /list, /shutdown')
    cmd_task = asyncio.create_task(server_commands(server))
    await cmd_task
    print('Server stopped')

asyncio.run(main())