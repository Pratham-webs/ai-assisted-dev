import tempfile
import unittest
from pathlib import Path

from student_tasks_api import create_app


class StudentTasksApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": str(Path(self.temp_dir.name) / "tasks.db"),
                "JWT_SECRET": "test-secret-that-is-at-least-32-characters",
            }
        )
        self.client = self.app.test_client()
        self.token = self.register_and_login("student@example.com")

    def tearDown(self):
        self.temp_dir.cleanup()

    def register_and_login(self, email):
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 201)
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 200)
        return response.json["token"]

    def headers(self, token=None, **extra):
        return {
            "Authorization": f"Bearer {token or self.token}",
            **extra,
        }

    def test_create_list_and_read_task(self):
        response = self.client.post(
            "/api/tasks",
            headers=self.headers(),
            json={
                "title": "Submit lab report",
                "description": "Finish the experiment write-up",
                "course": "Chemistry",
                "priority": "high",
                "dueDate": "2026-11-05",
            },
        )
        self.assertEqual(response.status_code, 201)
        task = response.json
        self.assertEqual(task["title"], "Submit lab report")
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["version"], 1)

        listing = self.client.get("/api/tasks", headers=self.headers())
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json["total"], 1)
        self.assertEqual(listing.json["items"][0]["id"], task["id"])

        detail = self.client.get(f"/api/tasks/{task['id']}", headers=self.headers())
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json["dueDate"], "2026-11-05")

    def test_rejects_invalid_task_without_saving(self):
        response = self.client.post(
            "/api/tasks",
            headers=self.headers(),
            json={"title": "   ", "dueDate": "2026-02-30"},
        )
        self.assertEqual(response.status_code, 400)
        fields = {issue["field"] for issue in response.json["fields"]}
        self.assertEqual(fields, {"title", "dueDate"})

        listing = self.client.get("/api/tasks", headers=self.headers())
        self.assertEqual(listing.json["total"], 0)

    def test_idempotency_key_creates_only_one_task(self):
        headers = self.headers(**{"Idempotency-Key": "retry-key-0001"})
        payload = {"title": "Read chapter"}
        first = self.client.post("/api/tasks", headers=headers, json=payload)
        retry = self.client.post("/api/tasks", headers=headers, json=payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(first.json["id"], retry.json["id"])

    def test_update_requires_current_version_and_increments_it(self):
        created = self.client.post(
            "/api/tasks", headers=self.headers(), json={"title": "Draft essay"}
        ).json

        conflict = self.client.patch(
            f"/api/tasks/{created['id']}",
            headers=self.headers(),
            json={"title": "New title", "version": 2},
        )
        self.assertEqual(conflict.status_code, 409)

        updated = self.client.patch(
            f"/api/tasks/{created['id']}",
            headers=self.headers(),
            json={"status": "completed", "version": 1},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["status"], "completed")
        self.assertEqual(updated.json["version"], 2)

    def test_tasks_are_private_to_their_owner(self):
        created = self.client.post(
            "/api/tasks", headers=self.headers(), json={"title": "Private task"}
        ).json
        other_token = self.register_and_login("other@example.com")

        response = self.client.get(
            f"/api/tasks/{created['id']}", headers=self.headers(other_token)
        )
        self.assertEqual(response.status_code, 404)

        listing = self.client.get("/api/tasks", headers=self.headers(other_token))
        self.assertEqual(listing.json["total"], 0)

    def test_authentication_is_required(self):
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
