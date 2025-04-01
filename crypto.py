import random
import string
import hashlib
import os
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

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