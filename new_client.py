import asyncio

#Объявляем IP-адрес и порт по которым клиент будет подключаться к серверу.
HOST = '127.0.0.1'
PORT = 9090

'''Функция отправки сообщений. Запускается бесконечный цикл ожидания ввода сообщения пользователем и отправки его серверу.
Если пользователь вводит /exit, то серверу отправляется сообщение, что клиент отключился и цикл завершается.'''
async def send_message(writer):
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

'''Функция приема сообщений. Бесконечный цикл ожидания сообщений от сервера и их вывода. 
Если сервер принудительно завершает работу, цикл завершается.'''
async def receive_message(reader):
    while True:
        msg = (await reader.readline()).decode().strip()
        if msg == '__server_shutdown__':
            break
        elif not msg:
            break
        print(msg)

'''Основная функция. Запускается функция подключения к серверу и выводится приветственное сообщение.
Пользователю предлагается ввести никнейм и после этого начинается отправка и прием сообщений.'''
async def main():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    print((await reader.readline()).decode().strip())
    print((await reader.readline()).decode().strip())
    nickname = input()
    writer.write((nickname + '\n').encode())
    await writer.drain()
    rcv_msg = asyncio.create_task(receive_message(reader))
    snd_msg = asyncio.create_task(send_message(writer))
    #Ожидание завершение хотя бы одной из задач. Если одна из них завершилась, то завершается и вторая.
    await asyncio.wait([rcv_msg, snd_msg], return_when=asyncio.FIRST_COMPLETED)
    rcv_msg.cancel()
    snd_msg.cancel()
    writer.close()
    await writer.wait_closed()

asyncio.run(main())