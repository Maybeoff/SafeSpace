import sys
import random
import string
import hashlib
import os
import json
import socket
import threading
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QLineEdit, 
                             QLabel, QFileDialog, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal

# Crypto functions
def generate_encryption_key():
    """Генерирует ключ шифрования"""
    return base64.urlsafe_b64encode(os.urandom(32))

def encrypt_ip(ip, key):
    """Шифрует IP-адрес с помощью ключа"""
    f = Fernet(key)
    return f.encrypt(ip.encode())

def decrypt_ip(encrypted_ip, key):
    """Расшифровывает IP-адрес с помощью ключа"""
    f = Fernet(key)
    return f.decrypt(encrypted_ip).decode()

def encrypt_data(data, key):
    """Шифрует данные с использованием ключа"""
    if isinstance(key, str):
        key = key.encode()
    if isinstance(data, str):
        data = data.encode()
    f = Fernet(key)
    return f.encrypt(data)

def decrypt_data(encrypted_data, key):
    """Расшифровывает данные с использованием ключа"""
    if isinstance(key, str):
        key = key.encode()
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode()

def save_key_to_file(server_ip, filename):
    """Сохраняет ключ и зашифрованный IP в файл"""
    key = generate_encryption_key()
    encrypted_ip = encrypt_ip(server_ip, key)
    data = {
        'key': key.decode(),
        'encrypted_ip': base64.b64encode(encrypted_ip).decode()
    }
    with open(filename, 'w') as f:
        json.dump(data, f)
    return key

def load_key_from_file(filename):
    """Загружает ключ и расшифровывает IP из файла"""
    with open(filename, 'r') as f:
        data = json.load(f)
    key = data['key'].encode()
    encrypted_ip = base64.b64decode(data['encrypted_ip'])
    ip = decrypt_ip(encrypted_ip, key)
    return key, ip

def generate_password():
    """Генерирует случайный пароль"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

# Network Thread
class NetworkThread(QThread):
    message_received = Signal(str)
    connection_lost = Signal()

    def __init__(self, socket, encryption_key):
        super().__init__()
        self.socket = socket
        self.encryption_key = encryption_key
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                decrypted_message = decrypt_data(data, self.encryption_key)
                self.message_received.emit(decrypted_message)
            except:
                break
        self.running = False
        self.connection_lost.emit()

    def stop(self):
        self.running = False

# Main Window
class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SafeSpace")
        self.setMinimumSize(600, 400)
        
        self.client_socket = None
        self.encryption_key = None
        self.network_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Кнопка выбора файла
        self.key_button = QPushButton("Выбрать файл key.2pk")
        self.key_button.clicked.connect(self.select_key_file)
        layout.addWidget(self.key_button)
        
        # Статус файла ключа
        self.key_label = QLabel("Файл key.2pk не выбран")
        layout.addWidget(self.key_label)
        
        # Кнопка подключения
        self.connect_button = QPushButton("Подключиться к серверу")
        self.connect_button.clicked.connect(self.connect_to_server)
        self.connect_button.setEnabled(False)
        layout.addWidget(self.connect_button)
        
        # Область чата
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        
        # Поле ввода сообщения и кнопка отправки
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setEnabled(False)
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setEnabled(False)
        input_layout.addWidget(self.send_button)
        layout.addLayout(input_layout)
        
        # Статус подключения
        self.status_label = QLabel("Статус: Отключено")
        layout.addWidget(self.status_label)
        
    def select_key_file(self):
        try:
            filename, _ = QFileDialog.getOpenFileName(self, "Выберите файл ключа", "", "Key Files (*.2pk)")
            if filename:
                self.encryption_key, self.server_ip = load_key_from_file(filename)
                self.key_label.setText(f"Выбран файл: {filename}")
                self.connect_button.setEnabled(True)
                self.add_to_chat("Файл ключа успешно загружен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл ключа: {str(e)}")
            
    def connect_to_server(self):
        try:
            if not self.encryption_key:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите файл ключа!")
                return
                
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            self.client_socket.connect((self.server_ip, 5000))
            self.client_socket.settimeout(None)
            
            # Запрашиваем никнейм
            nickname, ok = QInputDialog.getText(self, "Никнейм", "Введите ваш никнейм:")
            if ok and nickname:
                self.client_socket.send(encrypt_data(nickname, self.encryption_key))
                
                # Включаем элементы интерфейса
                self.message_input.setEnabled(True)
                self.send_button.setEnabled(True)
                self.connect_button.setEnabled(False)
                self.key_button.setEnabled(False)
                
                # Запускаем поток для получения сообщений
                self.network_thread = NetworkThread(self.client_socket, self.encryption_key)
                self.network_thread.message_received.connect(self.add_to_chat)
                self.network_thread.connection_lost.connect(self.handle_connection_lost)
                self.network_thread.start()
                
                self.add_to_chat("Успешно подключено к серверу")
                self.status_label.setText("Статус: Подключено")
            else:
                self.client_socket.close()
                self.client_socket = None
                
        except socket.timeout:
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к серверу: превышено время ожидания")
        except ConnectionRefusedError:
            QMessageBox.critical(self, "Ошибка", "Сервер не запущен или недоступен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу: {str(e)}")
            
    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            try:
                if not self.client_socket:
                    raise Exception("Соединение потеряно")
                self.client_socket.send(encrypt_data(message, self.encryption_key))
                self.message_input.clear()
            except:
                self.handle_connection_lost()
                
    def add_to_chat(self, message):
        self.chat_area.append(message)
        
    def handle_connection_lost(self):
        self.message_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.key_button.setEnabled(True)
        self.connect_button.setEnabled(False)
        self.status_label.setText("Статус: Соединение потеряно")
        self.add_to_chat("Соединение потеряно")
        
        if self.network_thread:
            self.network_thread.stop()
            self.network_thread = None
            
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
    def closeEvent(self, event):
        if self.network_thread:
            self.network_thread.stop()
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()