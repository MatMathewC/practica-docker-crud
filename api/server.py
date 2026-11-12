"""API CRUD educativa, sin paquetes externos (solo biblioteca estandar)."""
import json
import os
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from init_db import db_path, init_db

ITEM_PATH = re.compile(r"^/api/productos/(\d+)$")


def connect():
    db = sqlite3.connect(db_path(), timeout=5)
    db.row_factory = sqlite3.Row
    return db


def valid_product(body):
    if not isinstance(body, dict):
        raise ValueError("Se requiere un objeto JSON.")
    name = body.get("nombre")
    price = body.get("precio")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise ValueError("nombre debe tener entre 1 y 120 caracteres.")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not 0 <= price <= 1000000000:
        raise ValueError("precio debe ser un numero entre 0 y 1000000000.")
    return name.strip(), float(price)


class Handler(BaseHTTPRequestHandler):
    server_version = "PracticaCRUD/1.0"

    def json_response(self, status, data, extra_headers=None):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length invalido.") from exc
        if length <= 0 or length > 16_384:
            raise ValueError("El cuerpo JSON es obligatorio (maximo 16 KB).")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("JSON invalido o no UTF-8.") from exc

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/health":
                with connect() as db:
                    db.execute("SELECT 1")
                return self.json_response(200, {"status": "ok", "database": "ok"})
            if path == "/api/productos":
                with connect() as db:
                    rows = db.execute("SELECT * FROM productos ORDER BY id").fetchall()
                return self.json_response(200, [dict(row) for row in rows])
            match = ITEM_PATH.fullmatch(path)
            if match:
                with connect() as db:
                    row = db.execute("SELECT * FROM productos WHERE id = ?", (int(match.group(1)),)).fetchone()
                if row is None:
                    return self.json_response(404, {"error": "Producto no encontrado."})
                return self.json_response(200, dict(row))
            return self.json_response(404, {"error": "Ruta no encontrada."})
        except sqlite3.Error:
            return self.json_response(500, {"error": "Error de la base de datos."})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/productos":
            return self.json_response(404, {"error": "Ruta no encontrada."})
        try:
            name, price = valid_product(self.read_json())
            with connect() as db:
                cur = db.execute("INSERT INTO productos (nombre, precio) VALUES (?, ?)", (name, price))
                row = db.execute("SELECT * FROM productos WHERE id = ?", (cur.lastrowid,)).fetchone()
                db.commit()
            return self.json_response(201, dict(row), {"Location": f"/api/productos/{row['id']}"})
        except ValueError as exc:
            return self.json_response(400, {"error": str(exc)})
        except sqlite3.Error:
            return self.json_response(500, {"error": "Error de la base de datos."})

    def do_PUT(self):
        match = ITEM_PATH.fullmatch(urlsplit(self.path).path)
        if match is None:
            return self.json_response(404, {"error": "Ruta no encontrada."})
        try:
            name, price = valid_product(self.read_json())
            pk = int(match.group(1))
            with connect() as db:
                cur = db.execute("UPDATE productos SET nombre = ?, precio = ? WHERE id = ?", (name, price, pk))
                row = db.execute("SELECT * FROM productos WHERE id = ?", (pk,)).fetchone()
                db.commit()
            if cur.rowcount == 0:
                return self.json_response(404, {"error": "Producto no encontrado."})
            return self.json_response(200, dict(row))
        except ValueError as exc:
            return self.json_response(400, {"error": str(exc)})
        except sqlite3.Error:
            return self.json_response(500, {"error": "Error de la base de datos."})

    def do_DELETE(self):
        match = ITEM_PATH.fullmatch(urlsplit(self.path).path)
        if match is None:
            return self.json_response(404, {"error": "Ruta no encontrada."})
        try:
            with connect() as db:
                cur = db.execute("DELETE FROM productos WHERE id = ?", (int(match.group(1)),))
                db.commit()
            if cur.rowcount == 0:
                return self.json_response(404, {"error": "Producto no encontrado."})
            return self.json_response(200, {"mensaje": "Producto eliminado."})
        except sqlite3.Error:
            return self.json_response(500, {"error": "Error de la base de datos."})


def main():
    init_db()  # Permite el primer arranque sin pasos manuales adicionales.
    port = int(os.environ.get("PORT", "8000"))
    address = ("0.0.0.0", port)
    server = ThreadingHTTPServer(address, Handler)
    print(f"API lista en puerto {port}; SQLite: {db_path()}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
