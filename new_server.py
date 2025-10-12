import asyncio
from datetime import datetime

HOST = '127.0.0.1'
PORT = 9090

clients = {}
clients_lock  = asyncio.Lock()
clients_tasks = set()

async def server_commands(server):
    loop = asyncio.get_running_loop()
    while True:
        command = await loop.run_in_executor(None, input)
        if command == '/shutdown':
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

async def broadcast(client, nickname, message):
    for clnt in clients.values():
        if clnt != client:
            clnt.write(f'{datetime.now().strftime("%H:%M")} [{nickname}]: {message}\n'.encode())
            await clnt.drain()

async def handle_client(reader, writer):
    task = asyncio.current_task()
    clients_tasks.add(task)
    
    try:
        addr = writer.get_extra_info('peername')
        print(f'Client {addr} connected')
        writer.write('Вы подключились к серверу!\n'.encode())
        await writer.drain()
        
        while True:
            writer.write('Введите ваш никнейм:\n'.encode())
            await writer.drain()
            nickname = (await reader.readline()).decode().strip()
            if nickname in clients:
                writer.write('Никнейм уже занят\n'.encode())
                await writer.drain()
                continue
            break
        
        async with clients_lock:
            clients[nickname] = writer
        await broadcast(writer, nickname, 'Вошел в чат.')

        while True:
            try:
                data = await reader.readline()
                if not data:
                    break
                msg = data.decode().strip()
                if msg == '__disconnect__':
                    await broadcast(writer, nickname, 'Пользователь вышел из чата.')
                    async with clients_lock:
                        del clients[nickname]
                    break
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
        
async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print('Server started. Available commands: /list, /shutdown')
    cmd_task = asyncio.create_task(server_commands(server))
    await cmd_task
    print('Server stopped')

asyncio.run(main())