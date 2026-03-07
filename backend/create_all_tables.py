import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from app.core.database import Base  

from app.models.base import * 
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
