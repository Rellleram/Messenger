import socket
import threading

HOST = '127.0.0.1'
PORT = 9090

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

stop_flag = threading.Event()

def rcv_msg():
    while not stop_flag.is_set():
        try:
            msg = client.recv(1024).decode('utf-8')
            if not msg:
                print('Server closed connection')
                stop_flag.set()
                break
            print(msg)
        except OSError:
            break
        except Exception as e:
            print(f'Error receiving message: {e}')
            break

try:
    client.connect((HOST, PORT))
    print('Connected to server')
except ConnectionRefusedError:
    print('Connection failed')
    exit()

print(client.recv(1024).decode('utf-8'))
nickname = input()
client.send(nickname.encode('utf-8'))

threading.Thread(target=rcv_msg, daemon=True).start()
print('Введите сообщение. Для выхода введите /exit')
while not stop_flag.is_set():
    msg = input()
    if msg == '/exit':
        client.send('__disconnect__'.encode('utf-8'))
        stop_flag.set()
        break
    try:
        client.send(msg.encode('utf-8'))
    except:
        print('Не удалось отправить сообщение. Сервер недоступен.')

client.close()
