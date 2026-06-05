# DanceFlow

Локальный сайт школы танцев с рабочей регистрацией, входом и корзиной.

Фронтенд остается статическим HTML/CSS/JS, backend работает на FastAPI, данные хранятся в SQLite.

## Стек

- Python 3
- FastAPI
- Uvicorn
- SQLite
- Static HTML/CSS/JavaScript

## Запуск

Установить зависимости:

```bash
pip install -r requirements.txt
```

Запустить локальный сервер:

```bash
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Открыть сайт:

```text
http://127.0.0.1:8000
```

FastAPI отдает и API, и статический фронтенд. Отдельный frontend-сервер не нужен.

## Структура

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   └── danceflow.db
├── frontend/
│   ├── js/
│   │   ├── api.js
│   │   ├── app.js
│   │   ├── auth.js
│   │   └── cart.js
│   ├── index.html
│   ├── courses.html
│   ├── login.html
│   ├── register.html
│   ├── cart.html
│   └── styles.css
├── requirements.txt
└── README.md
```

## Backend

Основной файл backend:

```text
backend/app/main.py
```

При старте приложение:

- создает SQLite-базу `backend/danceflow.db`, если ее еще нет;
- создает таблицы пользователей, сессий, курсов, корзины и заявок;
- добавляет 6 базовых курсов в таблицу `courses`.

База локальная и не коммитится в git.

## Авторизация

Авторизация сделана через server-side cookie-сессии:

- пароль хранится как PBKDF2 hash;
- cookie называется `danceflow_session`;
- cookie выставляется как `HttpOnly`;
- фронтенд не хранит токен в `localStorage`.

Гость может смотреть сайт и курсы. Для добавления курса в корзину нужен вход.

## Корзина

Корзина привязана к пользователю. В MVP один курс добавляется в корзину один раз.

После оформления заявки:

- создается запись в `orders`;
- создаются позиции в `order_items`;
- корзина пользователя очищается.

## API

Healthcheck:

```http
GET /api/health
```

Курсы:

```http
GET /api/courses
```

Авторизация:

```http
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
POST /api/auth/logout
```

Корзина:

```http
GET    /api/cart
POST   /api/cart/items
DELETE /api/cart/items/{item_id}
POST   /api/cart/checkout
```

Пример регистрации:

```bash
curl -i -X POST http://127.0.0.1:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "firstName": "Иван",
    "lastName": "Иванов",
    "email": "ivan@example.com",
    "phone": "+7 999 123-45-67",
    "password": "secret123"
  }'
```

Пример добавления курса в корзину:

```bash
curl -i -X POST http://127.0.0.1:8000/api/cart/items \
  -H 'Content-Type: application/json' \
  -d '{"courseId": "ballet"}'
```

## Frontend

Общие JS-файлы:

- `frontend/js/api.js` - API-клиент на `fetch`;
- `frontend/js/app.js` - состояние шапки, текущий пользователь, logout, счетчик корзины;
- `frontend/js/auth.js` - обработчики форм входа и регистрации;
- `frontend/js/cart.js` - загрузка и рендер корзины.

Формы:

- `frontend/login.html` вызывает `handleLogin(event)`;
- `frontend/register.html` вызывает `handleRegister(event)`.

Курсы:

- `frontend/courses.html` содержит кнопки `В корзину`;
- если пользователь не вошел, его перекидывает на `login.html?next=courses.html`.

## Проверка

Проверить Python-синтаксис backend:

```bash
python3 -m py_compile backend/app/main.py
```

Проверить JS-синтаксис:

```bash
node --check frontend/js/api.js
node --check frontend/js/app.js
node --check frontend/js/auth.js
node --check frontend/js/cart.js
```

Быстрая проверка API:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/courses
```

## Сброс базы

Остановить сервер и удалить файл:

```bash
rm -f backend/danceflow.db
```

При следующем запуске FastAPI создаст базу заново и снова добавит курсы.

## Остановка

Если сервер запущен в терминале, остановить его можно через:

```text
Ctrl+C
```
