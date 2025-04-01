import socket
import json
import threading
import os
from crypto import encrypt_data, decrypt_data, save_key_to_file

class SecureChatServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.messages = []
        
        # Получаем локальный IP-адрес
        self.local_ip = self.get_local_ip()
        
        # Генерируем ключ шифрования и сохраняем его вместе с зашифрованным IP
        self.encryption_key = save_key_to_file(self.local_ip, 'key.2pk')
        print(f"Ключ шифрования сохранен в файл key.2pk")
        print(f"IP-адрес сервера: {self.local_ip}")
        
    def get_local_ip(self):
        """Получает локальный IP-адрес сервера"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return self.host
        
    def start(self):
        """Запускает сервер"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"Сервер запущен на {self.host}:{self.port}")
            print("Ожидание подключений...")
            
            while True:
                client_socket, address = self.server_socket.accept()
                print(f"Новое подключение от {address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_thread.start()
        except Exception as e:
            print(f"Ошибка запуска сервера: {e}")
            
    def handle_client(self, client_socket, address):
        """Обрабатывает подключение клиента"""
        try:
            # Получаем никнейм клиента
            nickname = decrypt_data(client_socket.recv(1024), self.encryption_key)
            self.clients[client_socket] = nickname
            print(f"Клиент {address} подключился как {nickname}")
            
            # Отправляем приветственное сообщение
            welcome_message = f"Добро пожаловать в чат, {nickname}!"
            client_socket.send(encrypt_data(welcome_message, self.encryption_key))
            
            while True:
                # Получаем сообщение от клиента
                message = decrypt_data(client_socket.recv(1024), self.encryption_key)
                if not message:
                    break
                    
                # Формируем сообщение с никнеймом
                full_message = f"{nickname}: {message}"
                print(f"Сообщение от {nickname}: {message}")
                self.messages.append(full_message)
                
                # Отправляем сообщение всем клиентам
                self.broadcast_message(full_message)
                
        except Exception as e:
            print(f"Ошибка при обработке клиента {address}: {e}")
        finally:
            if client_socket in self.clients:
                nickname = self.clients[client_socket]
                print(f"Клиент {nickname} ({address}) отключился")
                del self.clients[client_socket]
            client_socket.close()
            
    def broadcast_message(self, message):
        """Отправляет сообщение всем подключенным клиентам"""
        encrypted_message = encrypt_data(message, self.encryption_key)
        disconnected_clients = []
        
        for client in self.clients:
            try:
                client.send(encrypted_message)
            except:
                disconnected_clients.append(client)
                
        # Удаляем отключившихся клиентов
        for client in disconnected_clients:
            if client in self.clients:
                del self.clients[client]

if __name__ == "__main__":
    try:
        server = SecureChatServer()
        server.start()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
    except Exception as e:
        print(f"Критическая ошибка: {e}") 