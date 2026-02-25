import uvicorn
import sys
import os

# Ensure both the root directory and the backend directory are in the Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

if __name__ == "__main__":
    print("==================================================")
    print("Starting CRM AI SETU")
    print("-> Frontend UI : http://127.0.0.1:8000/frontend/template/index.html")
    print("-> Backend API : http://127.0.0.1:8000/docs")
    print("==================================================")
    
    # Run the FastAPI server mapped to the backend main file
    uvicorn.run(
        "app.main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )
