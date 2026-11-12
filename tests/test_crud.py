"""Pruebas de integración HTTP (sin Docker y sin paquetes adicionales)."""
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from server import Handler, ThreadingHTTPServer  # noqa: E402
from init_db import init_db  # noqa: E402


class CrudTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workdir = tempfile.TemporaryDirectory()
        cls.old_db = os.environ.get("DB_PATH")
        os.environ["DB_PATH"] = str(Path(cls.workdir.name) / "test.db")
        init_db()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=3)
        if cls.old_db is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = cls.old_db
        cls.workdir.cleanup()

    def req(self, method, url, data=None):
        raw = json.dumps(data).encode() if data is not None else None
        request = Request(f"http://127.0.0.1:{self.port}{url}", data=raw, method=method,
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=4) as res:
                return res.status, json.loads(res.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_01_health(self):
        status, body = self.req("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["database"], "ok")

    def test_02_create(self):
        status, data = self.req("POST", "/api/productos", {"nombre": "Cuaderno", "precio": 2.5})
        self.assertEqual(status, 201)
        self.assertEqual(data["nombre"], "Cuaderno")
        self.__class__.created_id = data["id"]

    def test_03_read_list_and_detail(self):
        status, rows = self.req("GET", "/api/productos")
        self.assertEqual(status, 200)
        self.assertTrue(any(p["id"] == self.created_id for p in rows))
        status, row = self.req("GET", f"/api/productos/{self.created_id}")
        self.assertEqual((status, row["nombre"]), (200, "Cuaderno"))

    def test_04_update(self):
        status, data = self.req("PUT", f"/api/productos/{self.created_id}", {"nombre": "Libro", "precio": 4})
        self.assertEqual(status, 200)
        self.assertEqual(data["nombre"], "Libro")

    def test_05_invalid_input(self):
        status, body = self.req("POST", "/api/productos", {"nombre": "", "precio": -1})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_06_delete_and_not_found(self):
        status, _ = self.req("DELETE", f"/api/productos/{self.created_id}")
        self.assertEqual(status, 200)
        status, _ = self.req("GET", f"/api/productos/{self.created_id}")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
