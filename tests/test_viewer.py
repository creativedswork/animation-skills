"""The viewer serves registered files only; fixtures are not animation evidence."""

import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import project
import viewer


class ViewerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model = self.root / ".artifacts/inputs/test.glb"
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"Synthetic HTTP fixture, not a GLB animation")
        project.write(self.root / "assets.json", {
            "test": {"path": ".artifacts/inputs/test.glb", "sha256": project.file_hash(self.model)}})
        case_dir = self.root / "cases/test-case"
        case_dir.mkdir(parents=True)
        project.write(case_dir / "case.json", {"id": "test-case", "inputs": ["test"]})
        (self.root / ".git").mkdir()
        (self.root / ".git/config").write_text("private repository data")
        (self.root / "viewer").mkdir()
        (self.root / "viewer/leak").symlink_to(self.root / ".git/config")
        handler = viewer.handler_for(self.root)
        handler.log_message = lambda *args: None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:" + str(self.server.server_port)

    def get(self, path):
        with urlopen(self.url + path, timeout=3) as response:
            return response.read()

    def test_catalog_and_registered_model_require_matching_bytes(self):
        task = json.loads(self.get("/api/cases"))["cases"][0]
        self.assertEqual(task["run_count"], 0)
        self.assertTrue(task["models"][0]["available"])
        self.assertEqual(self.get(task["models"][0]["url"]), self.model.read_bytes())
        self.model.write_bytes(b"changed after registration")
        task = json.loads(self.get("/api/cases"))["cases"][0]
        self.assertFalse(task["models"][0]["available"])
        with self.assertRaises(HTTPError) as error:
            self.get("/models/input-test")
        self.assertEqual(error.exception.code, 404)

    def test_repository_files_traversal_and_symlinks_are_not_served(self):
        for path in ("/.git/config", "/assets.json", "/viewer/../../.git/config",
                     "/viewer/%2e%2e/.git/config", "/viewer/leak"):
            with self.subTest(path=path), self.assertRaises(HTTPError) as error:
                self.get(path)
            self.assertIn(error.exception.code, (400, 404))


if __name__ == "__main__":
    unittest.main()
