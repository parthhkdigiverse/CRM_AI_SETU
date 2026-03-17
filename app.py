import uvicorn
import sys
import os
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
    port = int(os.getenv("SRM_PORT", 8000))

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
