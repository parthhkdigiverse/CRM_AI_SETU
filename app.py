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
    print("CRM AI SETU - Startup Diagnostics")
    print(f"Root Directory: {root_dir}")
    print(f"Backend Directory: {backend_dir}")
    print(f"Python Version: {sys.version}")
    print("--------------------------------------------------")
    print("-> Frontend UI : http://127.0.0.1:8000/frontend/template/index.html")
    print("-> Backend API : http://127.0.0.1:8000/docs")
    print("==================================================")
    
    print("Attempting to start uvicorn...")
    try:
        # Run the FastAPI server mapped to the backend main file
        uvicorn.run(
            "app.main:app", 
            host="127.0.0.1", 
            port=8000, 
            reload=True,
            reload_dirs=["backend"]
        )
    except Exception as e:
        print(f"Startup EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
