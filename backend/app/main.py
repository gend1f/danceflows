from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DB_PATH = BACKEND_DIR / "danceflow.db"

COOKIE_NAME = "danceflow_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24
REMEMBER_MAX_AGE_SECONDS = 60 * 60 * 24 * 30
PASSWORD_ITERATIONS = 210_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


COURSES = [
    {
        "slug": "ballet",
        "title": "Классический балет",
        "level": "Начальный",
        "price_monthly": 8000,
        "duration": "3 месяца",
        "group_size": "До 12 человек",
    },
    {
        "slug": "hiphop",
        "title": "Хип-хоп",
        "level": "Средний",
        "price_monthly": 9500,
        "duration": "2 месяца",
        "group_size": "До 15 человек",
    },
    {
        "slug": "contemporary",
        "title": "Контемпорари",
        "level": "Продвинутый",
        "price_monthly": 11000,
        "duration": "4 месяца",
        "group_size": "До 10 человек",
    },
    {
        "slug": "salsa",
        "title": "Сальса",
        "level": "Начальный",
        "price_monthly": 7500,
        "duration": "3 месяца",
        "group_size": "До 20 человек",
    },
    {
        "slug": "kids",
        "title": "Детская хореография",
        "level": "Детский",
        "price_monthly": 6500,
        "duration": "6 месяцев",
        "group_size": "До 10 человек",
    },
    {
        "slug": "jazz",
        "title": "Джаз-модерн",
        "level": "Средний",
        "price_monthly": 10000,
        "duration": "3 месяца",
        "group_size": "До 12 человек",
    },
]


class RegisterPayload(BaseModel):
    firstName: str
    lastName: str
    email: str
    phone: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str
    remember: bool = False


class CartItemPayload(BaseModel):
    courseId: str


app = FastAPI(title="DanceFlow API")


def utc_now() -> datetime:
    return datetime.utcnow()


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations_text),
        )
        return secrets.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def price_text(price_monthly: int) -> str:
    return f"{price_monthly:,}".replace(",", " ") + " ₽/мес"


@contextmanager
def db_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def user_to_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "firstName": row["first_name"],
        "lastName": row["last_name"],
        "email": row["email"],
        "phone": row["phone"],
        "createdAt": row["created_at"],
    }


def course_to_public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["slug"],
        "slug": row["slug"],
        "title": row["title"],
        "level": row["level"],
        "priceMonthly": row["price_monthly"],
        "price": price_text(row["price_monthly"]),
        "duration": row["duration"],
        "groupSize": row["group_size"],
    }


def create_session(
    connection: sqlite3.Connection,
    response: Response,
    user_id: int,
    remember: bool,
) -> None:
    token = secrets.token_urlsafe(32)
    max_age = REMEMBER_MAX_AGE_SECONDS if remember else SESSION_MAX_AGE_SECONDS
    expires_at = (utc_now() + timedelta(seconds=max_age)).isoformat(timespec="seconds")

    connection.execute(
        """
        INSERT INTO sessions (token_hash, user_id, expires_at, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (hash_token(token), user_id, expires_at, iso_now()),
    )
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def init_db() -> None:
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                level TEXT NOT NULL,
                price_monthly INTEGER NOT NULL,
                duration TEXT NOT NULL,
                group_size TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(user_id, course_id)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                total INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'created',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
                title TEXT NOT NULL,
                price_monthly INTEGER NOT NULL,
                quantity INTEGER NOT NULL
            );
            """
        )

        for course in COURSES:
            connection.execute(
                """
                INSERT INTO courses (slug, title, level, price_monthly, duration, group_size)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    level = excluded.level,
                    price_monthly = excluded.price_monthly,
                    duration = excluded.duration,
                    group_size = excluded.group_size
                """,
                (
                    course["slug"],
                    course["title"],
                    course["level"],
                    course["price_monthly"],
                    course["duration"],
                    course["group_size"],
                ),
            )


def get_current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Нужно войти")

    token_hash = hash_token(token)
    with db_connection() as connection:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (iso_now(),))
        row = connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, iso_now()),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла")

    return user_to_public(row)


def read_cart(connection: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    rows = connection.execute(
        """
        SELECT
            cart_items.id AS item_id,
            cart_items.quantity,
            courses.slug,
            courses.title,
            courses.level,
            courses.price_monthly,
            courses.duration,
            courses.group_size
        FROM cart_items
        JOIN courses ON courses.id = cart_items.course_id
        WHERE cart_items.user_id = ?
        ORDER BY cart_items.id
        """,
        (user_id,),
    ).fetchall()

    items = []
    total = 0
    for row in rows:
        line_total = row["price_monthly"] * row["quantity"]
        total += line_total
        items.append(
            {
                "id": row["item_id"],
                "quantity": row["quantity"],
                "course": {
                    "id": row["slug"],
                    "slug": row["slug"],
                    "title": row["title"],
                    "level": row["level"],
                    "priceMonthly": row["price_monthly"],
                    "price": price_text(row["price_monthly"]),
                    "duration": row["duration"],
                    "groupSize": row["group_size"],
                },
                "lineTotal": line_total,
            }
        )

    return {
        "items": items,
        "count": sum(item["quantity"] for item in items),
        "total": total,
        "totalText": price_text(total).replace("/мес", ""),
    }


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register")
def register(payload: RegisterPayload, response: Response) -> dict[str, Any]:
    email = normalize_email(payload.email)
    first_name = payload.firstName.strip()
    last_name = payload.lastName.strip()
    phone = payload.phone.strip()

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Некорректный email")
    if len(payload.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Пароль должен быть не короче 6 символов")
    if not first_name or not last_name or not phone:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Заполните все поля")

    with db_connection() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (email, password_hash, first_name, last_name, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (email, hash_password(payload.password), first_name, last_name, phone, iso_now()),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Пользователь с таким email уже существует") from exc

        user_id = cursor.lastrowid
        create_session(connection, response, user_id, remember=True)
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    return {"user": user_to_public(row)}


@app.post("/api/auth/login")
def login(payload: LoginPayload, response: Response) -> dict[str, Any]:
    email = normalize_email(payload.email)
    with db_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

        create_session(connection, response, row["id"], remember=payload.remember)

    return {"user": user_to_public(row)}


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": user}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with db_connection() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))

    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/courses")
def list_courses() -> dict[str, Any]:
    with db_connection() as connection:
        rows = connection.execute("SELECT * FROM courses ORDER BY id").fetchall()

    return {"courses": [course_to_public(row) for row in rows]}


@app.get("/api/cart")
def get_cart(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with db_connection() as connection:
        return read_cart(connection, user["id"])


@app.post("/api/cart/items")
def add_cart_item(
    payload: CartItemPayload,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    slug = payload.courseId.strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Курс не выбран")

    with db_connection() as connection:
        course = connection.execute("SELECT id FROM courses WHERE slug = ?", (slug,)).fetchone()
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Курс не найден")

        connection.execute(
            """
            INSERT INTO cart_items (user_id, course_id, quantity, created_at)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(user_id, course_id) DO UPDATE SET quantity = 1
            """,
            (user["id"], course["id"], iso_now()),
        )
        return read_cart(connection, user["id"])


@app.delete("/api/cart/items/{item_id}")
def remove_cart_item(
    item_id: int,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    with db_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM cart_items WHERE id = ? AND user_id = ?",
            (item_id, user["id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция корзины не найдена")

        return read_cart(connection, user["id"])


@app.post("/api/cart/checkout")
def checkout(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    with db_connection() as connection:
        cart = read_cart(connection, user["id"])
        if not cart["items"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Корзина пуста")

        cursor = connection.execute(
            "INSERT INTO orders (user_id, total, status, created_at) VALUES (?, ?, 'created', ?)",
            (user["id"], cart["total"], iso_now()),
        )
        order_id = cursor.lastrowid

        for item in cart["items"]:
            course = item["course"]
            connection.execute(
                """
                INSERT INTO order_items (order_id, course_id, title, price_monthly, quantity)
                SELECT ?, id, ?, ?, ?
                FROM courses
                WHERE slug = ?
                """,
                (
                    order_id,
                    course["title"],
                    course["priceMonthly"],
                    item["quantity"],
                    course["slug"],
                ),
            )

        connection.execute("DELETE FROM cart_items WHERE user_id = ?", (user["id"],))

    return {
        "order": {
            "id": order_id,
            "total": cart["total"],
            "totalText": cart["totalText"],
            "status": "created",
        },
        "cart": {"items": [], "count": 0, "total": 0, "totalText": "0 ₽"},
    }


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
def api_not_found(path: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API endpoint not found")


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def frontend_static(path: str) -> FileResponse:
    requested = (FRONTEND_DIR / path).resolve()
    frontend_root = FRONTEND_DIR.resolve()

    if requested.is_file() and requested.is_relative_to(frontend_root):
        return FileResponse(requested)

    not_found = FRONTEND_DIR / "404.html"
    if not_found.exists():
        return FileResponse(not_found, status_code=status.HTTP_404_NOT_FOUND)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Страница не найдена")
