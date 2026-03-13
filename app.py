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
    print("==================================================")
    print("SRM AI SETU - Startup Diagnostics")
    print(f"Root Directory: {root_dir}")
    print(f"Backend Directory: {backend_dir}")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print("--------------------------------------------------")
    print("-> Frontend UI : http://127.0.0.1:8000/frontend/template/index.html")
    print("-> Backend API : http://127.0.0.1:8000/docs")
    print("==================================================")
    
    # Reload mode can terminate unexpectedly in some Windows terminal flows.
    # Keep production-like startup stable by default, and allow explicit opt-in.
    enable_reload = os.getenv("SRM_RELOAD", "0").lower() in {"1", "true", "yes", "on"}
    
    # Port configuration - allow override via environment variable
    port = int(os.getenv("SRM_PORT", "8000"))

    print("Attempting to start uvicorn...")
    print(f"Reload Mode: {'ON' if enable_reload else 'OFF'} (set SRM_RELOAD=1 to enable)")
    print(f"Port: {port} (set SRM_PORT=xxxx to change)")
    try:
        # Run the FastAPI server mapped to the backend main file
        # server_header=False disables the Server header
        # Use loop='auto' and socket reuse options for Windows stability
        uvicorn.run(
            "app.main:app", 
            host="127.0.0.1", 
            port=port, 
            reload=enable_reload,
            reload_dirs=[backend_dir] if enable_reload else None,
            server_header=False,
            loop="auto"
        )
    except Exception as e:
        print(f"Startup EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
