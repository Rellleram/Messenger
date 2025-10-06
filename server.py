import socket

HOST = '127.0.0.1'
PORT = 9090

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print('Server started, waiting for connection...')

cl_sckt, addr = server.accept()

print('New connection!', addr)

msg = cl_sckt.recv(1024).decode('utf-8')

print('Message from client:', msg)

cl_sckt.send('Hello from server'.encode('utf-8'))

cl_sckt.close()
server.close()