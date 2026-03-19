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

from config.config import HOST, PORT
_display_host = "localhost" if HOST == "0.0.0.0" else HOST

def kill_process_on_port(port):
    """Automatically find and kill any process holding the specified port on Windows."""
    import subprocess
    import re
    try:
        # Find the PID(s) using the port
        cmd = f'netstat -ano | findstr :{port}'
        output = subprocess.check_output(cmd, shell=True).decode()
        pids = set(re.findall(r'\s+(\d+)$', output, re.MULTILINE))
        
        for pid in pids:
            if pid != '0':
                print(f"[Cleanup] Terminating conflicting process PID: {pid} on port {port}...")
                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=False)
    except subprocess.CalledProcessError:
        # This happens if no process is found (findstr returns exit code 1)
        pass
    except Exception as e:
        print(f"[Cleanup] Warning: Failed to clear port {port}: {e}")

if __name__ == "__main__":
    print("--------------------------------------------------")
    print(f"-> Frontend UI : http://{_display_host}:{PORT}/frontend/template/index.html")
    print(f"-> Backend API : http://{_display_host}:{PORT}/docs")
    print("==================================================")
    
    print("Attempting to start uvicorn...")
    try:
        # Clear the port before starting
        kill_process_on_port(PORT)
        
        # Run the FastAPI server mapped to the backend main file
        uvicorn.run(
            "backend.app.main:app", 
            host=HOST, 
            port=PORT,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n[Shutdown] Server stopped by user.")
    except Exception as e:
        print(f"Startup EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
