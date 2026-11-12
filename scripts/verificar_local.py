"""Comprobacion reproducible HTTP del CRUD sin necesidad de Docker."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def request(port, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def check(condition, step):
    if not condition:
        raise AssertionError(f"Fallo en {step}")


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env.update({"DB_PATH": str(Path(tmp) / "verificacion.db"), "PORT": str(port)})
        p = subprocess.Popen([sys.executable, "-u", str(ROOT / "api" / "server.py")],
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for attempt in range(40):
                try:
                    status, data = request(port, "GET", "/health")
                    if status == 200:
                        break
                except (OSError, URLError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("La API no inicio")
            check(data["database"] == "ok", "health")
            print("GET    /health             -> 200 OK (SQLite: ok)")
            status, data = request(port, "POST", "/api/productos", {"nombre": "Cuaderno", "precio": 2.5})
            check(status == 201, "POST")
            pk = data["id"]
            print(f"POST   /api/productos      -> {status} Creado (id={pk})")
            status, data = request(port, "GET", "/api/productos")
            check(status == 200 and len(data) == 1, "list")
            print(f"GET    /api/productos      -> {status} Lista (1 producto)")
            status, data = request(port, "GET", f"/api/productos/{pk}")
            check(status == 200 and data["nombre"] == "Cuaderno", "detail")
            print(f"GET    /api/productos/{pk}    -> {status} Detalle")
            status, data = request(port, "PUT", f"/api/productos/{pk}", {"nombre": "Libro", "precio": 4})
            check(status == 200 and data["nombre"] == "Libro", "PUT")
            print(f"PUT    /api/productos/{pk}    -> {status} Actualizado")
            status, data = request(port, "POST", "/api/productos", {"nombre": "", "precio": -3})
            check(status == 400, "invalid body")
            print(f"POST   /api/productos      -> {status} Validacion correcta")
            status, data = request(port, "DELETE", f"/api/productos/{pk}")
            check(status == 200, "delete")
            print(f"DELETE /api/productos/{pk}    -> {status} Eliminado")
            status, data = request(port, "GET", f"/api/productos/{pk}")
            check(status == 404, "not found")
            print(f"GET    /api/productos/{pk}    -> {status} No encontrado")
            print("RESULTADO: 8 verificaciones HTTP correctas; BD temporal aislada.")
        finally:
            p.terminate()
            try:
                p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=4)


if __name__ == "__main__":
    main()
