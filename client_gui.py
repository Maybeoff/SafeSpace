import sys
import socket
import threading
import os
import json
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                            QLabel, QMessageBox, QInputDialog, QFileDialog)
from PySide6.QtCore import Qt, Signal, QObject
from crypto import encrypt_data, decrypt_data, load_key_from_file

class SignalHandler(QObject):
    message_received = Signal(str)
    connection_status = Signal(str)

class SecureChatClientGUI(QMainWindow):
    def __init__(self, port=5000):
        super().__init__()
        self.port = port
        self.client_socket = None
        self.encryption_key = None
        self.server_ip = None
        self.signal_handler = SignalHandler()
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        self.setWindowTitle("Безопасный чат")
        self.setMinimumSize(600, 400)
        
        # Создаем центральный виджет и layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Кнопка выбора файла ключа
        self.key_button = QPushButton("Выбрать файл key.2pk")
        self.key_button.clicked.connect(self.select_key_file)
        layout.addWidget(self.key_button)
        
        # Информация о выбранном файле
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
        
        # Поле ввода сообщения
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение...")
        self.message_input.setEnabled(False)
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)
        
        # Кнопка отправки
        self.send_button = QPushButton("Отправить")
        self.send_button.setEnabled(False)
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Статус подключения
        self.status_label = QLabel("Статус: Отключено")
        layout.addWidget(self.status_label)
        
        # Подключаем сигналы
        self.signal_handler.message_received.connect(self.display_message)
        self.signal_handler.connection_status.connect(self.update_status)
        
    def select_key_file(self):
        """Выбор файла key.2pk"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите файл key.2pk",
                "",
                "Key files (*.2pk)"
            )
            if file_path:
                if not os.path.exists(file_path):
                    QMessageBox.critical(self, "Ошибка", "Файл не существует!")
                    return
                    
                # Загружаем данные из файла
                self.encryption_key, self.server_ip = load_key_from_file(file_path)
                
                self.key_label.setText(f"Выбран файл: {file_path}")
                self.connect_button.setEnabled(True)
                self.status_label.setText(f"Статус: Файл ключа загружен")
                self.chat_area.append(f"Файл ключа успешно загружен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл ключа: {e}")
                
    def connect_to_server(self):
        """Подключение к серверу"""
        try:
            if not self.encryption_key or not self.server_ip:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите файл ключа!")
                return
                
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)  # Таймаут подключения 5 секунд
            self.client_socket.connect((self.server_ip, self.port))
            self.client_socket.settimeout(None)  # Убираем таймаут после подключения
            
            # Запрашиваем никнейм
            nickname, ok = QInputDialog.getText(self, 'Никнейм', 'Введите ваш никнейм:')
            if ok and nickname:
                self.nickname = nickname
                self.client_socket.send(encrypt_data(nickname, self.encryption_key))
                self.signal_handler.connection_status.emit("Подключено")
                
                # Включаем элементы интерфейса
                self.message_input.setEnabled(True)
                self.send_button.setEnabled(True)
                self.key_button.setEnabled(False)
                self.connect_button.setEnabled(False)
                
                # Запускаем поток для получения сообщений
                receive_thread = threading.Thread(target=self.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                self.chat_area.append("Успешно подключено к серверу")
            else:
                if self.client_socket:
                    self.client_socket.close()
                self.client_socket = None
                
        except socket.timeout:
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к серверу: превышено время ожидания")
        except ConnectionRefusedError:
            QMessageBox.critical(self, "Ошибка", "Сервер не запущен или недоступен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу: {e}")
            
    def receive_messages(self):
        """Получение сообщений от сервера"""
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                message = decrypt_data(data, self.encryption_key)
                self.signal_handler.message_received.emit(message)
            except Exception as e:
                print(f"Ошибка получения сообщения: {e}")
                self.signal_handler.connection_status.emit("Соединение потеряно")
                break
                
    def send_message(self):
        """Отправка сообщения на сервер"""
        message = self.message_input.text().strip()
        if message:
            try:
                if not self.client_socket:
                    raise Exception("Соединение потеряно")
                self.client_socket.send(encrypt_data(message, self.encryption_key))
                self.message_input.clear()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось отправить сообщение: {e}")
                self.signal_handler.connection_status.emit("Соединение потеряно")
                
    def display_message(self, message):
        """Отображение сообщения в чате"""
        self.chat_area.append(message)
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )
        
    def update_status(self, status):
        """Обновление статуса подключения"""
        self.status_label.setText(f"Статус: {status}")
        if status == "Соединение потеряно":
            self.message_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.key_button.setEnabled(True)
            self.connect_button.setEnabled(True)
            if self.client_socket:
                try:
                    self.client_socket.close()
                except:
                    pass
                self.client_socket = None
            self.chat_area.append("Соединение потеряно")
        
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = SecureChatClientGUI()
    client.show()
    sys.exit(app.exec()) 