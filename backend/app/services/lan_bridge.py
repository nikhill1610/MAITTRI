"""
MAITRI LAN Bridge Service
-------------------------
Automatically bridges incoming IoT connections from LAN interfaces (e.g. ESP32, ESP8266)
to the local FastAPI uvicorn instance (127.0.0.1:8000).

This guarantees that physical IoT nodes can stream telemetry to the backend even if
uvicorn was started without '--host 0.0.0.0'. If uvicorn is already listening on
0.0.0.0, the bridge gracefully detects the occupied port and yields to uvicorn.
"""

import socket
import threading
import logging
import time
from typing import Set

logger = logging.getLogger("maitri.lan_bridge")

_bridge_running = False
_bound_ips: Set[str] = set()
_active_servers = []


def _pipe(source: socket.socket, dest: socket.socket):
    """Streams data bi-directionally between source and destination sockets."""
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            dest.sendall(data)
    except Exception:
        pass
    finally:
        try:
            dest.shutdown(socket.SHUT_WR)
        except Exception:
            pass


def _handle_client(client_sock: socket.socket, target_host: str = "127.0.0.1", target_port: int = 8000):
    """Bridges an accepted LAN client connection to the local backend port."""
    backend_sock = None
    try:
        backend_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        backend_sock.connect((target_host, target_port))

        t1 = threading.Thread(target=_pipe, args=(client_sock, backend_sock), daemon=True)
        t2 = threading.Thread(target=_pipe, args=(backend_sock, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=10.0)
        t2.join(timeout=10.0)
    except Exception as e:
        logger.debug(f"[LAN Bridge] Failed to connect to local backend: {e}")
    finally:
        if client_sock:
            try:
                client_sock.close()
            except Exception:
                pass
        if backend_sock:
            try:
                backend_sock.close()
            except Exception:
                pass


def _listen_on_ip(ip: str, port: int):
    """Listens on a specific LAN interface and proxies connections to 127.0.0.1:port."""
    srv = None
    try:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((ip, port))
        srv.listen(15)
        srv.settimeout(2.0)
        _active_servers.append(srv)
        print(f"[LAN Bridge] Successfully listening on {ip}:{port} -> 127.0.0.1:{port} for IoT nodes")

        while _bridge_running:
            try:
                client_sock, addr = srv.accept()
                print(f"[LAN Bridge] >>> INCOMING CONNECTION from {addr[0]}:{addr[1]} on {ip}:{port} <<<", flush=True)
                threading.Thread(target=_handle_client, args=(client_sock, "127.0.0.1", port), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[LAN Bridge] Error on {ip}:{port}: {e}", flush=True)
                break
    except OSError as e:
        # Port is already bound (e.g. uvicorn listening on 0.0.0.0 or another bridge instance)
        # This is expected and safe.
        pass
    finally:
        if srv:
            try:
                srv.close()
            except Exception:
                pass
        _bound_ips.discard(ip)


def start_lan_bridge(port: int = 8000):
    """
    Spawns background monitors to automatically bind any local non-loopback IP interfaces
    to forward traffic to 127.0.0.1:port.
    """
    global _bridge_running
    if _bridge_running:
        return
    _bridge_running = True

    def _monitor():
        while _bridge_running:
            try:
                hostname = socket.gethostname()
                _, _, ips = socket.gethostbyname_ex(hostname)
            except Exception:
                ips = []

            for ip in ips:
                if ip.startswith("127.") or ip in _bound_ips:
                    continue
                _bound_ips.add(ip)
                t = threading.Thread(target=_listen_on_ip, args=(ip, port), daemon=True)
                t.start()

            time.sleep(4)

    threading.Thread(target=_monitor, daemon=True).start()
