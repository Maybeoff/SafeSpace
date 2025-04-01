import sys
import socket
import threading
import os
import json
import base64
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                            QLabel, QMessageBox, QInputDialog, QFileDialog)
from PySide6.QtCore import Qt, Signal, QObject, Slot
from cryptography.fernet import Fernet

class SignalHandler(QObject):
    message_received = Signal(str)
    connection_status = Signal(str)

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SafeSpace")
        self.setMinimumSize(600, 400)
        
        self.client_socket = None
        self.encryption_key = None
        self.server_ip = None
        self.signal_handler = SignalHandler()
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
        
        # Подключаем сигналы
        self.signal_handler.message_received.connect(self.display_message)
        self.signal_handler.connection_status.connect(self.update_status)
        
    def select_key_file(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите файл key.2pk",
                "",
                "Key files (*.2pk)"
            )
            
            if not file_path:
                return
                
            if not os.path.exists(file_path):
                QMessageBox.critical(self, "Ошибка", "Файл не существует!")
                return
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if 'key' not in data or 'encrypted_ip' not in data:
                QMessageBox.critical(self, "Ошибка", "Неверный формат файла ключа")
                return
                
            self.encryption_key = data['key'].encode()
            encrypted_ip = base64.b64decode(data['encrypted_ip'])
            
            f = Fernet(self.encryption_key)
            self.server_ip = f.decrypt(encrypted_ip).decode()
            
            self.key_label.setText(f"Выбран файл: {file_path}")
            self.connect_button.setEnabled(True)
            self.status_label.setText("Статус: Файл ключа загружен")
            self.chat_area.append("Файл ключа успешно загружен")
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Ошибка", "Файл ключа поврежден или имеет неверный формат")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл ключа: {str(e)}")
            
    def connect_to_server(self):
        try:
            if not self.encryption_key or not self.server_ip:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите файл ключа!")
                return
                
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            self.client_socket.connect((self.server_ip, 5000))
            self.client_socket.settimeout(None)
            
            nickname, ok = QInputDialog.getText(self, 'Никнейм', 'Введите ваш никнейм:')
            if ok and nickname:
                self.nickname = nickname
                f = Fernet(self.encryption_key)
                self.client_socket.send(f.encrypt(nickname.encode()))
                self.signal_handler.connection_status.emit("Подключено")
                
                self.message_input.setEnabled(True)
                self.send_button.setEnabled(True)
                self.key_button.setEnabled(False)
                self.connect_button.setEnabled(False)
                
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу: {str(e)}")
            
    def receive_messages(self):
        f = Fernet(self.encryption_key)
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    print("Соединение закрыто сервером")
                    self.signal_handler.connection_status.emit("Соединение потеряно")
                    break
                    
                try:
                    message = f.decrypt(data).decode()
                    print(f"Получено сообщение: {message}")
                    self.signal_handler.message_received.emit(message)
                except Exception as decrypt_error:
                    print(f"Ошибка расшифровки: {decrypt_error}")
            except Exception as e:
                print(f"Ошибка получения сообщения: {str(e)}")
                self.signal_handler.connection_status.emit("Соединение потеряно")
                break
                
    def send_message(self):
        message = self.message_input.text().strip()
        if message:
            try:
                if not self.client_socket or not self.client_socket.fileno() != -1:
                    # Пробуем переподключиться
                    try:
                        print("Попытка переподключения...")
                        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client_socket.settimeout(5)
                        self.client_socket.connect((self.server_ip, 5000))
                        self.client_socket.settimeout(None)
                        
                        # Повторно отправляем никнейм
                        self.client_socket.send(Fernet(self.encryption_key).encrypt(self.nickname.encode()))
                        print("Переподключение успешно")
                        
                        # Перезапускаем поток приема сообщений
                        receive_thread = threading.Thread(target=self.receive_messages)
                        receive_thread.daemon = True
                        receive_thread.start()
                        
                    except Exception as reconnect_error:
                        raise Exception(f"Не удалось переподключиться: {str(reconnect_error)}")
                    
                print(f"Отправка сообщения: {message}")
                encrypted_message = Fernet(self.encryption_key).encrypt(message.encode())
                print(f"Зашифрованное сообщение: {encrypted_message}")
                
                self.client_socket.send(encrypted_message)
                print("Сообщение отправлено")
                
                self.message_input.clear()
                
            except Exception as e:
                print(f"Ошибка отправки: {str(e)}")
                QMessageBox.warning(self, "Ошибка", f"Не удалось отправить сообщение: {str(e)}")
                self.signal_handler.connection_status.emit("Соединение потеряно")
                
    @Slot(str)
    def display_message(self, message):
        """Отображает сообщение в чате"""
        print(f"Отображение сообщения: {message}")
        self.chat_area.append(message)
        # Прокручиваем чат вниз
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )
        
    @Slot(str)
    def update_status(self, status):
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