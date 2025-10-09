import socket
import threading
from multiprocessing import Value
import datetime

HOST = '127.0.0.1'
PORT = 9090

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = {}


def broadcast(client_socket, nick, message):
    for client in clients.values():
        if client != client_socket:
            client.send(f'{datetime.datetime.now().strftime("%H:%M")} [{nick}]: {message.decode("utf-8")}'.encode('utf-8'))

def server_commands(shutdown):
    while True:
        command = input()
        if command == '/list':
            print(f'Список клиентов:\n{clients}')
        elif command == '/shutdown':
            shutdown.value = True
            print("Server shutting down...")
            break
        else:
            print('Unknown command')

def msg_handler(client, nickname, shutdown):
    while not shutdown.value:
        try:
            msg = client.recv(1024)
            if not msg:
                break   
            elif msg.decode('utf-8') == '__disconnect__':
                for cl_sckt in clients.values():
                    if cl_sckt != client:
                        cl_sckt.send(f'Пользователь {nickname} отлючился от чата.'.encode('utf-8'))
                break
            
            broadcast(client, nickname, msg)   
        except Exception as e:
            print(f"Error receiving message: {e}")
            break
    with threading.Lock():
        print(f'Client {nickname} disconnected')
        del clients[nickname]
    client.close()
    print(f'Client {nickname} cleaned up')   

def receive():
    print('Server started')
    print('Available commands: /list, /shutdown')
    shutdown = Value('b', False)
    thread1 = threading.Thread(target=server_commands, args = (shutdown, ))
    thread1.start()
    server.settimeout(1.0)
    while not shutdown.value:
        try:
            cl_sckt, addr = server.accept()
            print(f'Client {addr} connected')
            cl_sckt.send('Вы подключились к серверу! Введите ваш никнейм'.encode('utf-8'))

            cl_nickname = cl_sckt.recv(1024).decode('utf-8')
            print(f'Client with address {addr} set nickname:', cl_nickname)
            for client in clients.values():
                if client != cl_sckt:
                    client.send(f'Пользователь {cl_nickname} подключился к чату!'.encode('utf-8'))
            clients[cl_nickname] = cl_sckt

            thread2 = threading.Thread(target=msg_handler, args=(cl_sckt, cl_nickname, shutdown))    
            thread2.start()
        except socket.timeout:
              continue
        except Exception as e:
            if shutdown.value:
                break
            print(f"Error accepting connection: {e}")

    print('Closing server...')
    server.close()

receive()