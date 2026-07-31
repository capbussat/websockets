#!/usr/bin/env python3
"""
Client WebSocket de supervisio.
Envia periodicament la propia IP al servidor i n'espera confirmacio.
"""
import asyncio
import argparse
import re
import socket
import subprocess
import sys

import websockets

DEFAULT_SERVER_IP = "1.2.3.4"
DEFAULT_SERVER_PORT = 8765
CLIENT_PORT = 8766      # port local del client (bind d'origen)
CONFIRM_TIMEOUT = 3    # segons d'espera per la confirmacio
RETRY_INTERVAL = 20     # segons entre enviaments
IFACE = "enp2s0"        # interficie de xarxa a consultar


def detect_own_ip(iface: str = IFACE) -> str:
    """Obté la IPv4 de la interfície indicada mitjançant 'ip addr'."""
    try:
        sortida = subprocess.run(
            ["ip", "-4", "-oneline", "addr", "show", "dev", iface],
            capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"No s'ha pogut consultar la interficie {iface}: {e}")

    match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", sortida)
    if not match:
        sys.exit(f"La interficie {iface} no té IPv4 assignada")

    return match.group(1)


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
    parser.add_argument("--iface", default=IFACE, help="Interficie de xarxa (per defecte enp2s0)")
    parser.add_argument("--my-ip", default=None, help="IP propia (per defecte, autodetectada de --iface)")
    args = parser.parse_args()

    my_ip = args.my_ip or detect_own_ip(args.iface)

    try:
        asyncio.run(send_heartbeat(args.server_ip, args.server_port, my_ip, args.local_port))
    except KeyboardInterrupt:
        print("\nClient aturat (CTRL+C)")
