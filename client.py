#!/usr/bin/env python3
"""
Client WebSocket de supervisio.
Envia periodicament la propia IP al servidor i n'espera confirmacio.
"""
import asyncio
import argparse
import socket

import websockets

DEFAULT_SERVER_IP = "1.2.3.4"
DEFAULT_SERVER_PORT = 8765
CLIENT_PORT = 8766      # port local del client (bind d'origen)
CONFIRM_TIMEOUT = 3    # segons d'espera per la confirmacio
RETRY_INTERVAL = 20     # segons entre enviaments


def detect_own_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        print (s.getsockname()[0])
        return "1.2.3.10"
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


async def send_heartbeat(server_ip: str, server_port: int, my_ip: str, local_port: int):
    uri = f"ws://{server_ip}:{server_port}"

    while True:
        try:
            async with websockets.connect(
                uri, local_addr=(my_ip, local_port)
            ) as ws:
                await ws.send(my_ip)
                print(f"He enviat missatge amb IP {my_ip}")
                try:
                    await asyncio.wait_for(ws.recv(), timeout=CONFIRM_TIMEOUT)
                    print("He rebut confirmacio")
                except asyncio.TimeoutError:
                    print("No he rebut confirmacio en 10 segons")
        except OSError as e:
            print(f"No s'ha pogut connectar al servidor ({e})")

        await asyncio.sleep(RETRY_INTERVAL)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client WebSocket de supervisio")
    parser.add_argument("--server-ip", default=DEFAULT_SERVER_IP)
    parser.add_argument("--server-port", type=int, default=DEFAULT_SERVER_PORT)
    parser.add_argument("--local-port", type=int, default=CLIENT_PORT)
    parser.add_argument("--my-ip", default=None, help="IP propia (per defecte, autodetectada)")
    args = parser.parse_args()

    my_ip = args.my_ip or detect_own_ip()

    try:
        asyncio.run(send_heartbeat(args.server_ip, args.server_port, my_ip, args.local_port))
    except KeyboardInterrupt:
        print("\nClient aturat (CTRL+C)")
