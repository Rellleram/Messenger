import socket
import threading
from cryptography.fernet import Fernet

HOST = '127.0.0.1'
PORT = 9090

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

stop_flag = threading.Event()


def encr(msg):
    return cipher.encrypt(msg)
def decr(msg):
    return cipher.decrypt(msg)

def rcv_msg():
    while not stop_flag.is_set():
        try:
            msg = decr(client.recv(1024)).decode('utf-8')
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
    key = client.recv(1024)
    cipher = Fernet(key)
except ConnectionRefusedError:
    print('Connection failed')
    exit()

print(decr(client.recv(1024)).decode('utf-8'))
nickname = input()
client.send(encr(nickname.encode('utf-8')))

threading.Thread(target=rcv_msg, daemon=True).start()
print('Введите сообщение. Для выхода введите /exit')
while not stop_flag.is_set():
    msg = input()
    if msg == '/exit':
        client.send(encr('__disconnect__'.encode('utf-8')))
        stop_flag.set()
        break
    try:
        client.send(encr(msg.encode('utf-8')))
    except:
        print('Не удалось отправить сообщение. Сервер недоступен.')

client.close()
