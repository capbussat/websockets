#!/usr/bin/env python3
"""
Servidor WebSocket de supervisio (versio amb Threads, sense asyncio).
Espera missatges dels clients (la seva propia IP), manté un registre
dels que s'han connectat en els darrers 60 segons i mostra per
terminal una llista ordenada. Nomes respon als clients presents a
ALLOWED_CLIENTS.
"""
import argparse
import threading
import time
from datetime import datetime, timedelta

from websockets.sync.server import serve
from websockets.exceptions import ConnectionClosed

DEFAULT_SERVER_IP = "1.2.3.4"
DEFAULT_SERVER_PORT = 8765
TIMEOUT_WINDOW = 60      # segons: finestra de "actiu"
STATUS_INTERVAL = 10     # segons entre impressions d'estat

# Llista inicial de clients permesos (editar segons la xarxa)
ALLOWED_CLIENTS = [
    "1.2.3.10",
    "1.2.3.11",
    "1.2.3.12",
]

clients_seen: dict[str, datetime] = {}   # ip -> darrer contacte
lock = threading.Lock()


def handler(websocket):
    origin_ip = websocket.remote_address[0]
    if origin_ip not in ALLOWED_CLIENTS:
        return  # ni tan sols cal llegir el missatge

    try:
        for message in websocket:
            client_ip = message.strip()
            if client_ip != origin_ip:
                print(f"AVÍS: IP declarada ({client_ip}) no coincideix "
                      f"amb IP d'origen ({origin_ip}), descartat")
                continue
            with lock:
                clients_seen[origin_ip] = datetime.now()
            websocket.send("OK")
    except ConnectionClosed:
        pass


def print_status_loop():
    while True:
        time.sleep(STATUS_INTERVAL)
        now = datetime.now()
        with lock:
            actius = sorted(
                ip for ip, ts in clients_seen.items()
                if now - ts <= timedelta(seconds=TIMEOUT_WINDOW)
            )
            ultims = dict(clients_seen)
        print(f"\n[{now:%H:%M:%S}] Clients actius (<{TIMEOUT_WINDOW}s): {len(actius)}")
        for ip in actius:
            antiguitat = (now - ultims[ip]).seconds
            print(f"  - {ip}  (fa {antiguitat}s)")


def main(host: str, port: int):
    print(f"Servidor escoltant a ws://{host}:{port}")
    print(f"Clients permesos: {', '.join(ALLOWED_CLIENTS)}")

    threading.Thread(target=print_status_loop, daemon=True).start()

    with serve(handler, host, port) as server:
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor WebSocket de supervisio")
    parser.add_argument("--ip", default=DEFAULT_SERVER_IP, help="IP on escoltar")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help="Port")
    args = parser.parse_args()

    try:
        main(args.ip, args.port)
    except KeyboardInterrupt:
        print("\nServidor aturat (CTRL+C)")
