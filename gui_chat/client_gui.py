import socket
import ssl
import threading
import base64
from PySide6.QtWidgets import (QApplication, 
                               QWidget, 
                               QPushButton, 
                               QVBoxLayout,
                               QHBoxLayout,
                               QLineEdit,
                               QTextEdit,
                               QLabel,
                               QStackedLayout,
                               QMessageBox
)
from PySide6.QtCore import Qt, QObject, Signal, QThread, QMetaObject, Slot
from PySide6.QtGui import QPixmap
from rules import rules_login, rules_password, rules_nickname
from icon_data import image_data

def create_icon_from_base64(base64_string):
    """Создает QPixmap из строки Base64"""
    try:
        image_bytes = base64.b64decode(base64_string)
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        return pixmap
    except Exception as e:
        print(f"Ошибка загрузки иконки из Base64: {e}")
        return QPixmap()  # Возвращаем пустую иконку

HOST = '127.0.0.1'
PORT = 9090

class Client(QObject):
     
    def __init__(self):
        super().__init__()
    
    sock = None
    ssl_sock = None
    connected_success = Signal()
    connected_failed = Signal(str)
    welcome_received = Signal(str)
    login_success = Signal(str, list)
    login_failed = Signal(str)
    registration_success = Signal(str)
    registration_failed = Signal(str)
    message_received = Signal(str)
    server_shutdown = Signal()
    client_disconnected = Signal()

    @Slot()
    def connect_to_server(self):
        '''Подключение к серверу'''
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)

            ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED

            CERT = '''-----BEGIN CERTIFICATE-----
-----END CERTIFICATE-----'''

            ssl_ctx.load_verify_locations(cadata=CERT)
            
            # Оборачиваем socket в SSL
            self.ssl_sock = ssl_ctx.wrap_socket(self.sock, server_hostname=HOST)
            self.ssl_sock.connect((HOST, PORT))
            
            # Таймаут для чтения/записи
            self.ssl_sock.settimeout(0.5)

            welcome_msg = self.recv_line()

            if welcome_msg:
                self.welcome_received.emit(welcome_msg)
            
            self.connected_success.emit()
        
        except Exception as e:
            self.connected_failed.emit(str(e))

    def recv_line(self):
        data = b''
        while not data.endswith(b'\n'):
            chunk = self.ssl_sock.recv(1)
            if not chunk:
                raise ConnectionError('Connection closed')
            data += chunk
        return data.decode().strip()
    
    def login(self, login, password):
        '''Аутентификация пользователя'''
        threading.Thread(target=self._login_thread, args=(login, password), daemon=True).start()
    
    
    def _login_thread(self, login, password):
        self.ssl_sock.sendall('__login__\n'.encode())

        self.ssl_sock.sendall((login + '\n').encode())
        self.ssl_sock.sendall((password + '\n').encode())

        answer = self.recv_line()

        if answer == '__login_success__':
            nickname = self.recv_line()

            history_len = self.recv_line()
            history = []

            for _ in range(int(history_len)):
                msg = self.recv_line()
                history.append(msg)

            self.login_success.emit(nickname, history)
            self._start_receiving()
        elif answer == '__bad_data__':
            self.login_failed.emit('Неверные логин/пароль')
        else:
            self.login_failed.emit('Произошла ошибка')

    def registration(self, login, password, nickname):
        threading.Thread(target=self._registration_thread, args=(login, password, nickname), daemon=True).start()

    def _registration_thread(self, login, password, nickname):
        self.ssl_sock.sendall('__registration__\n'.encode())

        self.ssl_sock.sendall((login + '\n').encode())
        self.ssl_sock.sendall((password + '\n').encode())
        self.ssl_sock.sendall((nickname + '\n').encode())

        answer = self.recv_line()

        if answer == '__registration_success__':
            self.registration_success.emit('Вы успешно зарегистрировались!')
        elif answer == '__login_error__':
            self.registration_failed.emit('Логин не соответствует требованиям. Попробуйте еще раз.')
        elif answer == '__password_error__':
            self.registration_failed.emit('Пароль не соответствует требованиям. Попробуйте еще раз.')
        elif answer == '__nickname_error__':
            self.registration_failed.emit('Никнейм не соответствует требованиям. Попробуйте еще раз.')
        elif answer == '__username_exists__':
            self.registration_failed.emit('Пользователь с таким логином уже зарегистрирован.')
        elif answer == '__nickname_exists__':
            self.registration_failed.emit('Пользователь с таким никнеймом уже зарегистрирован.')    
        else:
            self.registration_failed.emit('Произошла ошибка')

    def send_message(self, msg):
        '''Отправка сообщения'''
        self.ssl_sock.sendall((msg + '\n').encode())
    
    def _start_receiving(self):
        '''Запуск потока для приема сообщений от сервера'''
        thread = threading.Thread(target=self._receive_messages)
        thread.daemon = True
        thread.start()

    def _receive_messages(self):
        '''Прием сообщений от сервера'''
        while self.ssl_sock:
            try:
                msg = self.recv_line()
                
                if msg == "__server_shutdown__":
                    self.server_shutdown.emit()
                    break
                else:
                    self.message_received.emit(msg)
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Ошибка приема сообщений: {e}")
                break

client = Client()

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Общий чат')
        self.setGeometry(50, 50, 400, 300)

        self.stacked_layout = QStackedLayout()
        
        # Создаем экраны
        self._create_connection_screen()
        self._create_login_screen()
        self._create_register_screen()
        self._create_chat_screen()

        # Устанавливаем начальный экран
        self.setLayout(self.stacked_layout)
        self.stacked_layout.setCurrentIndex(0)
        
        # Подключаем сигналы клиента
        self._connect_client_signals()

      
    def _connect_client_signals(self):
        '''Подключение сигналов клиента к слотам'''
        client.connected_success.connect(self.on_connected_success)
        client.connected_failed.connect(self.on_connected_failed)
        client.welcome_received.connect(self.on_welcome_received)
        client.message_received.connect(self.on_message_received)
        client.login_success.connect(self.on_login_success)
        client.login_failed.connect(self.on_login_failed)
        client.registration_success.connect(self.on_registration_success)
        client.registration_failed.connect(self.on_registration_failed)
        
    def on_connected_success(self):
        '''Переключаем экран при успешном входе'''
        self.stacked_layout.setCurrentIndex(1)
    
    def on_connected_failed(self, error):
        '''Ошибка подключения'''
        QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу:\n{error}")
    
    def on_welcome_received(self, msg):
        '''Обработка приветственного сообщения'''
        QMessageBox.information(self, "Приветственное сообщение", msg)

    def on_login_clicked(self):
        '''Обработка нажатия кнопки входа'''
        login = self.login_enter_input.text()
        password = self.password_enter_input.text()
        
        client.login(login, password)
    
    def on_login_success(self, nickname, history):
        '''Обработка успешного входа'''
        QMessageBox.information(self, 'Добро пожаловать', f'Ваш никнейм в чате: {nickname}')
        self.stacked_layout.setCurrentIndex(3)

        self.chat_messages.clear()
    
        # Добавляем историю сообщений
        if history:
            for msg in history:
                self.chat_messages.append(msg)
        else:
            self.chat_messages.append("История сообщений пуста")
        
    def on_login_failed(self, error):
        QMessageBox.critical(self, 'Ошибка', error)
        self.stacked_layout.setCurrentIndex(1)
    
    def on_register_clicked(self):
        '''Обработка нажатия кнопки регистрации'''
        login = self.login_register_input.text()
        password = self.password_register_input.text()
        nickname = self.nickname_register_input.text()
        
        client.registration(login, password, nickname)
    
    def on_registration_success(self, msg):
        QMessageBox.information(self, 'Регистрация', msg)
        self.stacked_layout.setCurrentIndex(1)
    
    def on_registration_failed(self, error):
        QMessageBox.critical(self, 'Ошибка', error)
        self.stacked_layout.setCurrentIndex(2)

    def on_message_received(self, msg):
        self.chat_messages.append(msg)
    
    def on_send_clicked(self):
        msg = self.chat_input.text()
        client.send_message(msg)
        self.chat_input.clear()

    def _create_connection_screen(self):
        '''Экран подключения'''
        screen = QWidget()
        layout = QVBoxLayout()
        
        label = QLabel("Подключение к серверу...")
        label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        layout.addWidget(label)
        screen.setLayout(layout)
        self.stacked_layout.addWidget(screen)
        
    def _create_login_screen(self):
        '''Окно входа'''
        login_screen = QWidget()
        login_layout = QVBoxLayout()

        login_enter_label = QLabel('Логин:')
        self.login_enter_input = QLineEdit()

        password_enter_label = QLabel('Пароль:')
        self.password_enter_input = QLineEdit()
        self.password_enter_input.setEchoMode(QLineEdit.Password)
        login_button = QPushButton('Вход')
        login_button.clicked.connect(self.on_login_clicked)

        go_to_register_button = QPushButton('Регистрация')
        go_to_register_button.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(2))

        login_layout.addWidget(login_enter_label)
        login_layout.addWidget(self.login_enter_input)
        login_layout.addWidget(password_enter_label)
        login_layout.addWidget(self.password_enter_input)
        login_layout.addWidget(login_button)
        login_layout.addWidget(go_to_register_button)
        login_screen.setLayout(login_layout)
        self.stacked_layout.addWidget(login_screen)

    def _create_register_screen(self):
        '''Окно регистрации'''
        register_screen = QWidget()
        register_layout = QVBoxLayout()

        # Загружаем иконку
        info_pixmap = create_icon_from_base64(image_data)
        
        # Логин
        login_label_layout = QHBoxLayout()
        login_label = QLabel('Логин')
        login_info = QLabel()
        login_info.setPixmap(info_pixmap)
        login_info.setToolTip(rules_login())

        login_label_layout.addWidget(login_label)
        login_label_layout.addWidget(login_info)
        login_label_layout.addStretch()

        self.login_register_input = QLineEdit()

        register_layout.addLayout(login_label_layout)
        register_layout.addWidget(self.login_register_input)

        # Пароль
        password_label_layout = QHBoxLayout()
        password_label = QLabel('Пароль')
        password_info = QLabel()
        password_info.setPixmap(info_pixmap)
        password_info.setToolTip(rules_password())

        password_label_layout.addWidget(password_label)
        password_label_layout.addWidget(password_info)
        password_label_layout.addStretch()

        self.password_register_input = QLineEdit()
        self.password_register_input.setEchoMode(QLineEdit.Password)

        register_layout.addLayout(password_label_layout)
        register_layout.addWidget(self.password_register_input)
        # Никнейм
        nickname_label_layout = QHBoxLayout()
        nickname_label = QLabel('Никнейм')
        nickname_info = QLabel()
        nickname_info.setPixmap(info_pixmap)
        nickname_info.setToolTip(rules_nickname())

        nickname_label_layout.addWidget(nickname_label)
        nickname_label_layout.addWidget(nickname_info)
        nickname_label_layout.addStretch()

        self.nickname_register_input = QLineEdit()

        register_layout.addLayout(nickname_label_layout)
        register_layout.addWidget(self.nickname_register_input)
    
        # Кнопки
        register_button = QPushButton('Зарегистрироваться')
        register_button.clicked.connect(self.on_register_clicked)

        go_back_button = QPushButton('Вернуться к экрану входа')
        go_back_button.clicked.connect(lambda: self.stacked_layout.setCurrentIndex(1))

        register_layout.addWidget(register_button)
        register_layout.addWidget(go_back_button)

        register_screen.setLayout(register_layout)
        self.stacked_layout.addWidget(register_screen)
    
    def _create_chat_screen(self):
        '''Окно чата'''
        chat_screen = QWidget()
        chat_layout = QVBoxLayout()

        self.chat_messages = QTextEdit()
        self.chat_messages.setReadOnly(True)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText('Введите сообщение...')
        chat_send_button = QPushButton('Отправить')
        chat_send_button.clicked.connect(self.on_send_clicked)

        chat_layout.addWidget(self.chat_messages)
        chat_layout.addWidget(self.chat_input)
        chat_layout.addWidget(chat_send_button)
        chat_screen.setLayout(chat_layout)
        self.stacked_layout.addWidget(chat_screen)

app = QApplication()
thread = QThread()
client.moveToThread(thread)
thread.start()

window = MainWindow()
window.show()

QMetaObject.invokeMethod(client, 'connect_to_server', Qt.QueuedConnection)

app.exec()

thread.quit()
thread.wait()