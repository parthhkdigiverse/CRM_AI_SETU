import uvicorn
import sys
import os

# Define paths
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

# Ensure paths are in sys.path once and correctly
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    # Port configuration - allow override via environment variable
    port = int(os.getenv("SRM_PORT", "8080"))
    
    # Reload mode can terminate unexpectedly in some Windows terminal flows.
    # Keep production-like startup stable by default, and allow explicit opt-in.
    enable_reload = os.getenv("SRM_RELOAD", "0").lower() in {"1", "true", "yes", "on"}

    def clear_port(p):
        """Automatically kills any process using the specified port on Windows."""
        import subprocess
        import time
        try:
            # Find PID using the port (Windows specific)
            output = subprocess.check_output(f'netstat -ano | findstr :{p}', shell=True).decode()
            pids = set()
            for line in output.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.strip().split()
                    if len(parts) > 0:
                        pid = parts[-1]
                        pids.add(pid)
            
            for pid in pids:
                if pid != '0': # Avoid system process
                    print(f"[Port Guard] Port {p} is in use by PID {pid}. Terminating...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=False)
                    print(f"[Port Guard] PID {pid} signal sent.")
            
            
            if pids:
                time.sleep(1) # Give Windows time to release the socket
        except subprocess.CalledProcessError:
            pass
        except Exception as e:
            print(f"[Port Guard] Warning: {e}")

    print("==================================================")
    print("SRM AI SETU - Startup Diagnostics")
    clear_port(port)
    print(f"Root Directory: {root_dir}")
    print(f"Backend Directory: {backend_dir}")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print("--------------------------------------------------")
    print(f"-> Frontend UI : http://127.0.0.1:{port}/frontend/template/index.html")
    print(f"-> Backend API : http://127.0.0.1:{port}/docs")
    print("==================================================")

    print(f"Attempting to start uvicorn on port {port}...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            uvicorn.run(
                "app.main:app", 
                host="127.0.0.1", 
                port=port, 
                reload=enable_reload,
                reload_dirs=[backend_dir] if enable_reload else None,
                server_header=False,
                loop="auto"
            )
            break # Success
        except Exception as e:
            if "10048" in str(e) and attempt < max_retries - 1:
                print(f"[Startup] Port {port} still busy, retrying in 2s... (Attempt {attempt+1}/{max_retries})")
                import time
                time.sleep(2)
                clear_port(port) # Try clearing again
            else:
                print(f"Startup EXCEPTION: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
