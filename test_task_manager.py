import tempfile
import unittest
from pathlib import Path

from task_manager import create_task, list_tasks


class TaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp_dir.name) / "tasks.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_saves_task_fields_and_lists_saved_task(self):
        task_id = create_task(
            self.database,
            "Submit lab report",
            "Finish the experiment write-up",
            "2026-11-05",
            "Chemistry",
            "high",
        )

        self.assertEqual(task_id, 1)
        self.assertEqual(
            list_tasks(self.database),
            [(1, "Submit lab report", "Finish the experiment write-up", "2026-11-05", "Chemistry", "high")],
        )

    def test_saves_task_with_optional_fields_omitted(self):
        create_task(self.database, "Review lecture notes")

        self.assertEqual(
            list_tasks(self.database),
            [(1, "Review lecture notes", None, None, None, "medium")],
        )

    def test_rejects_blank_title_without_creating_task(self):
        with self.assertRaisesRegex(ValueError, "title is required"):
            create_task(self.database, "   ")

        self.assertEqual(list_tasks(self.database), [])

    def test_rejects_invalid_due_date(self):
        for invalid_date in ("next Friday", "20261105", "2026-02-30"):
            with self.subTest(due_date=invalid_date):
                with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
                    create_task(self.database, "Submit essay", due_date=invalid_date)

        self.assertEqual(list_tasks(self.database), [])


if __name__ == "__main__":
    unittest.main()
