# SafeSpace

Безопасный чат с шифрованием сообщений и графическим интерфейсом.

## Особенности

- Шифрование всех сообщений с использованием Fernet (симметричное шифрование)
- Графический интерфейс на PySide6
- Автоматическое шифрование IP-адреса сервера
- Поддержка никнеймов
- Защищенное хранение ключей в файле
- Звуковые уведомления о новых сообщениях
- Уведомления в системном трее
- История сообщений (последние 100 сообщений)

## Требования

- Python 3.7+
- PySide6
- cryptography
- playsound
- pystray

## Установка

### Вариант 1: Запуск из исходного кода

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите сервер:
```bash
python server.py
```

3. Запустите клиент:
```bash
python cgs.py
```

### Вариант 2: Запуск из exe-файла

1. Скачайте последнюю версию из раздела Releases
2. Распакуйте архив
3. Запустите `safespace.exe`

## Использование

### Сервер

1. Запустите `server.py` или `safespace.exe` с параметром `--server`
2. Сервер автоматически создаст файл `key.2pk` с ключом шифрования и зашифрованным IP-адресом
3. Раздайте файл `key.2pk` клиентам, которые должны подключиться к серверу

### Клиент

1. Запустите `cgs.py` или `safespace.exe`
2. Нажмите кнопку "Выбрать файл key.2pk" и выберите полученный файл ключа
3. Нажмите "Подключиться к серверу"
4. Введите свой никнейм
5. Начните общение!

## Безопасность

- Все сообщения шифруются с использованием Fernet (реализация AES)
- IP-адрес сервера хранится в зашифрованном виде
- Ключи шифрования генерируются с использованием криптографически стойкого генератора случайных чисел
- Для каждой сессии создается новый ключ

## Создание exe-файла

Для создания исполняемого файла:

1. Установите PyInstaller:
```bash
pip install pyinstaller
```

2. Создайте exe-файл:
```bash
pyinstaller --onefile --windowed --icon=icon.ico safespace.py
```

Исполняемый файл будет создан в папке `dist`.

## Решение проблем

1. Если появляется ошибка "Сервер не запущен или недоступен":
   - Убедитесь, что `server.py` запущен
   - Проверьте файервол

2. Если появляется ошибка при загрузке ключа:
   - Убедитесь, что используете правильный файл `key.2pk`
   - Попробуйте сгенерировать новый ключ, перезапустив сервер

3. Если не работает звук:
   - Убедитесь, что файл `newmaseg.wav` находится в той же папке, что и программа
   - Проверьте, включен ли звук в системе

## Структура проекта

- `cgs.py` - основной файл клиента (Combined GUI System), объединяющий функционал crypto.py и client_gui.py
- `server.py` - сервер чата требует crypto.py
- `requirements.txt` - зависимости проекта
- `key.2pk` - файл с ключом шифрования (генерируется автоматически)
- `crypto.py` - модуль с функциями шифрования, теперь включен в cgs.py
### Устаревшие файлы
- `client_gui.py` - (устаревший) клиент с графическим интерфейсом, теперь включен в cgs.py требует crypto.py

> Примечание: Файлы `crypto.py` и `client_gui.py` больше не используются, так как их функционал объединен в `cgs.py` для упрощения установки и использования.

## Примечания

- Не передавайте файл `key.2pk` через незащищенные каналы связи
- Для каждой новой сессии рекомендуется генерировать новый ключ
- При потере соединения клиент автоматически попытается переподключиться

