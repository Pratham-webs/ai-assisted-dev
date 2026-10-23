import argparse
import sqlite3
import sys
from contextlib import closing
from datetime import date


PRIORITIES = ("low", "medium", "high")


def validate_task(title, description, due_date, course, priority):
    title = title.strip()
    if not title:
        raise ValueError("title is required")
    if len(title) > 200:
        raise ValueError("title must be 200 characters or fewer")

    if description is not None and len(description) > 2000:
        raise ValueError("description must be 2000 characters or fewer")

    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
        except ValueError as exc:
            raise ValueError("due date must use YYYY-MM-DD format") from exc
        if parsed_due_date.isoformat() != due_date:
            raise ValueError("due date must use YYYY-MM-DD format")
    else:
        due_date = None

    course = course.strip() if course else None
    if course and len(course) > 100:
        raise ValueError("course must be 100 characters or fewer")

    priority = priority.lower()
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of: {', '.join(PRIORITIES)}")

    return title, description, due_date, course, priority


def create_task(database, title, description=None, due_date=None, course=None, priority="medium"):
    title, description, due_date, course, priority = validate_task(
        title, description, due_date, course, priority
    )

    with closing(sqlite3.connect(database)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    course TEXT,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor = connection.execute(
                """
                INSERT INTO tasks (title, description, due_date, course, priority)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, description, due_date, course, priority),
            )
            task_id = cursor.lastrowid

    return task_id


def list_tasks(database):
    with closing(sqlite3.connect(database)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_date TEXT,
                    course TEXT,
                    priority TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            return connection.execute(
                """
                SELECT id, title, description, due_date, course, priority
                FROM tasks
                ORDER BY id
                """
            ).fetchall()


def build_parser():
    parser = argparse.ArgumentParser(description="Record and view academic tasks.")
    parser.add_argument(
        "--database",
        default="academic_tasks.db",
        help="database file to use (default: academic_tasks.db)",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="record a new academic task")
    create.add_argument("--title", required=True, help="task title (required)")
    create.add_argument("--description", help="optional task description")
    create.add_argument("--due-date", help="optional due date in YYYY-MM-DD format")
    create.add_argument("--course", help="optional course or category")
    create.add_argument(
        "--priority",
        choices=PRIORITIES,
        default="medium",
        help="task priority (default: medium)",
    )

    commands.add_parser("list", help="show recorded academic tasks")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            task_id = create_task(
                args.database,
                args.title,
                args.description,
                args.due_date,
                args.course,
                args.priority,
            )
            print(f"Task saved successfully (ID: {task_id}).")
        else:
            tasks = list_tasks(args.database)
            if not tasks:
                print("No tasks recorded yet.")
                return 0

            for task_id, title, description, due_date, course, priority in tasks:
                print(f"#{task_id} {title}")
                print(f"  Due: {due_date or 'Not set'} | Course: {course or 'Not set'} | Priority: {priority}")
                if description:
                    print(f"  Description: {description}")
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
