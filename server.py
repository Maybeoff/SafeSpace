import socket
import threading
import json
import os
import base64
from cryptography.fernet import Fernet

class ChatServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {client_socket: nickname}
        self.encryption_key = None
        self.message_history = []  # История сообщений
        self.max_history = 100  # Максимальное количество сообщений в истории
        self.load_or_create_key()

    def load_or_create_key(self):
        """Загружает существующий ключ или создает новый"""
        try:
            if os.path.exists('key.2pk'):
                print("Загрузка существующего ключа...")
                with open('key.2pk', 'r') as f:
                    data = json.load(f)
                self.encryption_key = data['key'].encode()
                print("Ключ успешно загружен")
            else:
                print("Создание нового ключа...")
                self.create_new_key()
                print("Новый ключ создан и сохранен")
        except Exception as e:
            print(f"Ошибка при работе с ключом: {e}")
            print("Создание нового ключа...")
            self.create_new_key()

    def create_new_key(self):
        """Создает новый ключ и сохраняет его"""
        self.encryption_key = base64.urlsafe_b64encode(os.urandom(32))
        
        # Получаем локальный IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()

        # Шифруем IP
        f = Fernet(self.encryption_key)
        encrypted_ip = f.encrypt(local_ip.encode())

        # Сохраняем ключ и зашифрованный IP
        data = {
            'key': self.encryption_key.decode(),
            'encrypted_ip': base64.b64encode(encrypted_ip).decode()
        }
        
        with open('key.2pk', 'w') as f:
            json.dump(data, f)

    def verify_client_key(self, client_socket):
        """Проверяет, что клиент использует правильный ключ"""
        try:
            print("Ожидание данных от клиента для проверки ключа...")
            data = client_socket.recv(1024)
            if not data:
                print("Клиент закрыл соединение при проверке ключа")
                return False, None
                
            try:
                print(f"Получены данные для проверки: {data}")
                f = Fernet(self.encryption_key)
                nickname = f.decrypt(data).decode()
                print(f"Успешная проверка ключа, никнейм: {nickname}")
                return True, nickname
            except Exception as e:
                print(f"Ошибка проверки ключа: {str(e)}")
                return False, None
                
        except Exception as e:
            print(f"Ошибка при получении данных для проверки ключа: {str(e)}")
            return False, None

    def start(self):
        """Запускает сервер"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Сервер запущен на {self.host}:{self.port}")
            
            while True:
                client_socket, address = self.server_socket.accept()
                print(f"Новое подключение с {address}")
                
                # Проверяем ключ клиента
                is_valid, nickname = self.verify_client_key(client_socket)
                
                if is_valid and nickname:
                    print(f"Клиент {nickname} успешно подключен")
                    self.clients[client_socket] = nickname
                    
                    # Отправляем приветственное сообщение
                    welcome_msg = f"Добро пожаловать, {nickname}!"
                    self.send_encrypted_message(client_socket, welcome_msg)
                    
                    # Оповещаем всех о новом участнике
                    self.broadcast_message(f"{nickname} присоединился к чату", client_socket)
                    
                    # Запускаем поток для обработки сообщений клиента
                    thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                    thread.daemon = True
                    thread.start()
                else:
                    print(f"Клиент {address} использует неверный ключ")
                    client_socket.close()
                    
        except Exception as e:
            print(f"Ошибка сервера: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client_socket):
        """Обрабатывает сообщения от клиента"""
        f = Fernet(self.encryption_key)
        
        try:
            # Отправляем историю сообщений новому клиенту
            if self.message_history:
                history_message = "HISTORY:" + json.dumps(self.message_history)
                self.send_encrypted_message(client_socket, history_message)
            
            while True:
                try:
                    data = client_socket.recv(4096)  # Увеличиваем размер буфера для файлов
                    if not data:
                        print("Клиент закрыл соединение")
                        break
                        
                    print(f"Получены данные от клиента: {data}")
                    
                    # Расшифровываем сообщение
                    decrypted_message = f.decrypt(data).decode()
                    print(f"Расшифровано сообщение: {decrypted_message}")
                    
                    # Проверяем тип сообщения
                    if decrypted_message.startswith("FILE:"):
                        # Обработка файла
                        file_data = json.loads(decrypted_message[5:])
                        file_message = f"FILE:{json.dumps(file_data)}"
                        self.add_to_history(file_message)
                        self.broadcast_message(file_message)
                    else:
                        # Обычное текстовое сообщение
                        nickname = self.clients.get(client_socket, "Unknown")
                        full_message = f"{nickname}: {decrypted_message}"
                        self.add_to_history(full_message)
                        self.broadcast_message(full_message)
                    
                except Exception as e:
                    print(f"Ошибка обработки сообщения: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"Ошибка соединения с клиентом: {str(e)}")
        finally:
            self.remove_client(client_socket)

    def broadcast_message(self, message, sender_socket=None):
        """Отправляет сообщение всем клиентам"""
        print(f"Рассылка сообщения: {message}")
        f = Fernet(self.encryption_key)
        encrypted_message = f.encrypt(message.encode())
        print(f"Зашифрованное сообщение для рассылки: {encrypted_message}")
        
        # Создаем копию списка клиентов, чтобы избежать изменения во время итерации
        clients = list(self.clients.items())
        
        for client_socket, nickname in clients:
            try:
                print(f"Отправка сообщения клиенту {nickname}")
                client_socket.send(encrypted_message)
                print(f"Сообщение успешно отправлено клиенту {nickname}")
            except Exception as e:
                print(f"Ошибка отправки клиенту {nickname}: {e}")
                self.remove_client(client_socket)

    def send_encrypted_message(self, client_socket, message):
        """Отправляет зашифрованное сообщение конкретному клиенту"""
        try:
            f = Fernet(self.encryption_key)
            encrypted_message = f.encrypt(message.encode())
            client_socket.send(encrypted_message)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

    def remove_client(self, client_socket):
        """Удаляет клиента и оповещает остальных"""
        if client_socket in self.clients:
            nickname = self.clients[client_socket]
            del self.clients[client_socket]
            client_socket.close()
            self.broadcast_message(f"{nickname} покинул чат")
            print(f"Клиент {nickname} отключен")

    def stop(self):
        """Останавливает сервер"""
        if self.server_socket:
            self.server_socket.close()
        for client_socket in list(self.clients.keys()):
            client_socket.close()
        print("Сервер остановлен")

    def add_to_history(self, message):
        """Добавляет сообщение в историю"""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)  # Удаляем самое старое сообщение

if __name__ == "__main__":
    server = ChatServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
        server.stop() 