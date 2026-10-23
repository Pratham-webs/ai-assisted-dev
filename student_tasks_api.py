import os
import re
import sqlite3
from datetime import date, datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any
from uuid import uuid4

import jwt
from flask import Flask, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


PRIORITIES = ("low", "medium", "high")
STATUSES = ("pending", "completed")
TASK_FIELDS = {
    "title": "title",
    "description": "description",
    "course": "course",
    "priority": "priority",
    "status": "status",
    "dueDate": "due_date",
}
SORT_COLUMNS = {
    "dueDate": "due_date",
    "priority": "priority",
    "status": "status",
    "course": "course",
    "createdAt": "created_at",
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get("DATABASE", "student-tasks.db"),
        JWT_SECRET=os.environ.get("JWT_SECRET"),
        MAX_CONTENT_LENGTH=20 * 1024,
    )
    if config:
        app.config.update(config)

    secret = app.config["JWT_SECRET"]
    if not isinstance(secret, str) or len(secret) < 32:
        raise RuntimeError("Set JWT_SECRET to a random string of at least 32 characters.")

    initialize_database(app.config["DATABASE"])

    @app.teardown_appcontext
    def close_database(_error: BaseException | None = None) -> None:
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(error="Request body must be 20 KB or smaller."), 413

    @app.errorhandler(404)
    def route_not_found(_error):
        return jsonify(error="Not found."), 404

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Request failed", exc_info=error)
        return jsonify(error="The request could not be completed."), 500

    @app.post("/api/auth/register")
    def register():
        payload, error_response = json_object()
        if error_response:
            return error_response

        errors = {}
        email = payload.get("email")
        password = payload.get("password")
        if not isinstance(email, str):
            errors["email"] = "Enter a valid email address."
        else:
            email = email.strip().lower()
            if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
                errors["email"] = "Enter a valid email address of 254 characters or fewer."
        if not isinstance(password, str) or not 12 <= len(password) <= 128:
            errors["password"] = "Password must be between 12 and 128 characters."
        if errors:
            return validation_response(errors)

        user_id = str(uuid4())
        try:
            get_database().execute(
                "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
                (user_id, email, generate_password_hash(password)),
            )
            get_database().commit()
        except sqlite3.IntegrityError as error:
            get_database().rollback()
            if "users.email" in str(error):
                return jsonify(error="That email is already registered."), 409
            raise
        return jsonify(id=user_id, email=email), 201

    @app.post("/api/auth/login")
    def login():
        payload, error_response = json_object()
        if error_response:
            return error_response

        email = payload.get("email")
        password = payload.get("password")
        errors = {}
        if not isinstance(email, str) or len(email.strip()) > 254 or not EMAIL_PATTERN.fullmatch(email.strip()):
            errors["email"] = "Enter a valid email address."
        if not isinstance(password, str) or not 1 <= len(password) <= 128:
            errors["password"] = "Password is required and must be 128 characters or fewer."
        if errors:
            return validation_response(errors)

        user = get_database().execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            return jsonify(error="Email or password is incorrect."), 401

        token = jwt.encode(
            {
                "sub": user["id"],
                "exp": datetime.now(timezone.utc).timestamp() + 3600,
            },
            app.config["JWT_SECRET"],
            algorithm="HS256",
        )
        return jsonify(token=token)

    @app.get("/api/tasks")
    @authenticated
    def list_tasks():
        errors = {}
        status = request.args.get("status")
        priority = request.args.get("priority")
        course = request.args.get("course")
        sort = request.args.get("sort", "dueDate")
        order = request.args.get("order", "asc")
        page = parse_integer_query("page", 1, 1, None, errors)
        limit = parse_integer_query("limit", 20, 1, 100, errors)

        if status is not None and status not in STATUSES:
            errors["status"] = "Choose pending or completed."
        if priority is not None and priority not in PRIORITIES:
            errors["priority"] = "Choose low, medium, or high."
        if course is not None and len(course) > 120:
            errors["course"] = "Course must be 120 characters or fewer."
        if sort not in SORT_COLUMNS:
            errors["sort"] = "Choose dueDate, priority, status, course, or createdAt."
        if order not in ("asc", "desc"):
            errors["order"] = "Choose asc or desc."
        if errors:
            return validation_response(errors)

        conditions = ["owner_id = ?"]
        values: list[Any] = [g.user_id]
        for field, value in (("status", status), ("priority", priority), ("course", course)):
            if value is not None:
                conditions.append(f"{field} = ?")
                values.append(value)
        where = " AND ".join(conditions)
        database = get_database()
        total = database.execute(
            f"SELECT COUNT(*) AS count FROM tasks WHERE {where}", values
        ).fetchone()["count"]
        rows = database.execute(
            f"""
            SELECT * FROM tasks WHERE {where}
            ORDER BY {SORT_COLUMNS[sort]} {order.upper()}, id ASC
            LIMIT ? OFFSET ?
            """,
            (*values, limit, (page - 1) * limit),
        ).fetchall()
        return jsonify(
            items=[public_task(row) for row in rows],
            total=total,
            page=page,
            limit=limit,
        )

    @app.post("/api/tasks")
    @authenticated
    def create_task():
        payload, error_response = json_object()
        if error_response:
            return error_response
        values, errors = validate_task_fields(payload, creating=True)
        if errors:
            return validation_response(errors)

        key = request.headers.get("Idempotency-Key")
        if key is not None and not 8 <= len(key) <= 128:
            return jsonify(error="Idempotency-Key must be 8–128 characters."), 400

        database = get_database()
        with database:
            database.execute("BEGIN IMMEDIATE")
            if key is not None:
                prior = database.execute(
                    "SELECT task_id FROM idempotency_keys WHERE owner_id = ? AND key = ?",
                    (g.user_id, key),
                ).fetchone()
                if prior is not None:
                    existing = database.execute(
                        "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
                        (prior["task_id"], g.user_id),
                    ).fetchone()
                    if existing is None:
                        return jsonify(error="This retry key was already used."), 409
                    return jsonify(public_task(existing)), 200

            now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            task_id = str(uuid4())
            database.execute(
                """
                INSERT INTO tasks
                    (id, owner_id, title, description, course, priority, status,
                     due_date, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    task_id,
                    g.user_id,
                    values["title"],
                    values.get("description"),
                    values.get("course"),
                    values.get("priority", "medium"),
                    values.get("status", "pending"),
                    values.get("dueDate"),
                    now,
                    now,
                ),
            )
            if key is not None:
                database.execute(
                    "INSERT INTO idempotency_keys (owner_id, key, task_id) VALUES (?, ?, ?)",
                    (g.user_id, key, task_id),
                )
            task = database.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return jsonify(public_task(task)), 201

    @app.get("/api/tasks/<task_id>")
    @authenticated
    def get_task(task_id: str):
        task = get_database().execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
            (task_id, g.user_id),
        ).fetchone()
        if task is None:
            return jsonify(error="Task not found."), 404
        return jsonify(public_task(task))

    @app.patch("/api/tasks/<task_id>")
    @authenticated
    def update_task(task_id: str):
        payload, error_response = json_object()
        if error_response:
            return error_response
        values, errors = validate_task_fields(payload, creating=False)
        if errors:
            return validation_response(errors)

        database = get_database()
        task = database.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
            (task_id, g.user_id),
        ).fetchone()
        if task is None:
            return jsonify(error="Task not found."), 404
        if values["version"] != task["version"]:
            return jsonify(error="Task changed. Refresh before saving."), 409

        fields_to_update = [field for field in TASK_FIELDS if field in values]
        assignments = [f"{TASK_FIELDS[field]} = ?" for field in fields_to_update]
        update_values = [values[field] for field in fields_to_update]
        assignments.extend(("version = version + 1", "updated_at = ?"))
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        update_values.extend((now, task_id, g.user_id, values["version"]))
        result = database.execute(
            f"""
            UPDATE tasks SET {", ".join(assignments)}
            WHERE id = ? AND owner_id = ? AND version = ?
            """,
            update_values,
        )
        database.commit()
        if not result.rowcount:
            return jsonify(error="Task changed. Refresh before saving."), 409

        updated = database.execute(
            "SELECT * FROM tasks WHERE id = ? AND owner_id = ?",
            (task_id, g.user_id),
        ).fetchone()
        return jsonify(public_task(updated))

    @app.delete("/api/tasks/<task_id>")
    @authenticated
    def delete_task(task_id: str):
        result = get_database().execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?",
            (task_id, g.user_id),
        )
        get_database().commit()
        if not result.rowcount:
            return jsonify(error="Task not found."), 404
        return "", 204

    return app


def initialize_database(database_path: str) -> None:
    path = Path(database_path)
    if str(database_path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as database:
        database.execute("PRAGMA journal_mode = WAL")
        database.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES users(id),
                title TEXT NOT NULL,
                description TEXT,
                course TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'pending',
                due_date TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                owner_id TEXT NOT NULL,
                key TEXT NOT NULL,
                task_id TEXT NOT NULL,
                PRIMARY KEY (owner_id, key)
            );
            CREATE INDEX IF NOT EXISTS tasks_owner_idx ON tasks(owner_id);
            """
        )


def get_database() -> sqlite3.Connection:
    if "database" not in g:
        database = sqlite3.connect(
            current_app.config["DATABASE"],
            timeout=5,
        )
        database.row_factory = sqlite3.Row
        database.execute("PRAGMA foreign_keys = ON")
        g.database = database
    return g.database


def authenticated(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "")
        match = re.match(r"^Bearer\s+(.+)$", authorization, re.IGNORECASE)
        if match is None:
            return jsonify(error="Sign in required."), 401
        try:
            claims = jwt.decode(
                match.group(1),
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
            )
            user_id = claims.get("sub")
            if not isinstance(user_id, str) or not user_id:
                raise jwt.InvalidTokenError("Missing subject")
        except jwt.PyJWTError:
            return jsonify(error="Invalid or expired session."), 401
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapped


def json_object() -> tuple[dict[str, Any], Any | None]:
    if not request.is_json:
        return {}, (jsonify(error="Content-Type must be application/json."), 400)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {}, (jsonify(error="Request body must be a JSON object."), 400)
    return payload, None


def validate_task_fields(
    payload: dict[str, Any], creating: bool
) -> tuple[dict[str, Any], dict[str, str]]:
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}

    for field in TASK_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field == "title":
            if not isinstance(value, str):
                errors[field] = "Title must be text."
            else:
                value = value.strip()
                if not value:
                    errors[field] = "Title is required."
                elif len(value) > 200:
                    errors[field] = "Title must be 200 characters or fewer."
        elif field == "description":
            if value is not None and (not isinstance(value, str) or len(value) > 5000):
                errors[field] = "Description must be text of 5,000 characters or fewer."
        elif field == "course":
            if value is not None and not isinstance(value, str):
                errors[field] = "Course must be text."
            elif isinstance(value, str):
                value = value.strip()
                if len(value) > 120:
                    errors[field] = "Course must be 120 characters or fewer."
        elif field == "priority" and value not in PRIORITIES:
            errors[field] = "Choose low, medium, or high."
        elif field == "status" and value not in STATUSES:
            errors[field] = "Choose pending or completed."
        elif field == "dueDate":
            if value is not None:
                try:
                    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
                        raise ValueError
                except ValueError:
                    errors[field] = "Use a valid date in YYYY-MM-DD format."
        if field not in errors:
            values[field] = value

    if creating and "title" not in payload:
        errors["title"] = "Title is required."
    if not creating:
        version = payload.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            errors["version"] = "Version must be a positive integer."
        else:
            values["version"] = version
        if not any(field in payload for field in TASK_FIELDS):
            errors["_request"] = "Provide at least one task field to update."
    return values, errors


def parse_integer_query(
    field: str,
    default: int,
    minimum: int,
    maximum: int | None,
    errors: dict[str, str],
) -> int:
    raw_value = request.args.get(field)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        errors[field] = "Enter a valid integer."
        return default
    if value < minimum or (maximum is not None and value > maximum):
        upper_limit = f" and at most {maximum}" if maximum is not None else ""
        errors[field] = f"Value must be at least {minimum}{upper_limit}."
        return default
    return value


def validation_response(errors: dict[str, str]):
    return jsonify(
        error="Please correct the highlighted fields.",
        fields=[{"field": field, "message": message} for field, message in errors.items()],
    ), 400


def public_task(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "course": row["course"],
        "priority": row["priority"],
        "status": row["status"],
        "dueDate": row["due_date"],
        "version": row["version"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


if __name__ == "__main__":
    application = create_app()
    port = int(os.environ.get("PORT", "3000"))
    application.run(host="127.0.0.1", port=port)
