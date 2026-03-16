import uvicorn
import sys
import os
import socket
import signal

# -- Windows signal blocking -------------------------------------------------
if os.name == "nt":
    import ctypes
    import time
    _handler_t = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong)
    _start_time = time.time()

    @_handler_t
    def _win_ctrl_handler(ctrl_type):
        if ctrl_type == 0:  # CTRL_C_EVENT
            elapsed = time.time() - _start_time
            print(f"[DEBUG] CTRL_C at {elapsed:.1f}s", flush=True)
            if elapsed < 15:
                return True  # Block
            return False  # Allow
        return ctrl_type in {2, 5, 6}

    ctypes.windll.kernel32.SetConsoleCtrlHandler(_win_ctrl_handler, True)

# -- SIGTERM / SIGBREAK debug -----------------------------------------------
def _sig_debug(sig, frame):
    print(f"[DEBUG] Signal received: {sig}", flush=True)


signal.signal(signal.SIGTERM, _sig_debug)
try:
    signal.signal(signal.SIGBREAK, _sig_debug)  # Windows Ctrl+Break
except (OSError, AttributeError):
    pass

root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    host = os.getenv("SRM_HOST", "127.0.0.1")
    port = 8000


    def _port_free(h, p):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex((h, p)) != 0

    if not _port_free(host, port):
        print(f"[Startup] Port {port} is busy — killing existing process...", flush=True)
        if os.name == "nt":
            import subprocess
            try:
                out = subprocess.check_output(
                    f'netstat -ano | findstr ":{port} "',
                    shell=True
                ).decode()
                for line in out.strip().splitlines():
                    if "LISTENING" in line:
                        pid = line.strip().split()[-1]
                        if pid not in ("0", str(os.getpid())):
                            subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
                            print(f"[Startup] Killed PID {pid} on port {port}.", flush=True)
                import time
                time.sleep(1)  # Wait for port to be released
            except Exception as e:
                print(f"[Startup] Could not auto-kill: {e}", flush=True)
                sys.exit(1)
        else:
            print(f"[Startup] Port {port} is busy. Stop the existing process and retry.", flush=True)
            sys.exit(1)

    print("=" * 50)
    print("  SRM AI SETU")
    print(f"  Frontend : http://{host}:{port}/frontend/template/index.html")
    print(f"  API Docs : http://{host}:{port}/docs")
    print("=" * 50, flush=True)

    print("[DEBUG] About to call uvicorn.run...", flush=True)
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        server_header=False,
    )
    print("[DEBUG] uvicorn.run() returned - server exited.", flush=True)
