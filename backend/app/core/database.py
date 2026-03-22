from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client: AsyncIOMotorClient = None
db = None

async def connect_to_mongo():
    global client, db
    # settings.MONGODB_URI mathi connection thase
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    
    # 1. Ahiya tame fixed database name pan muki shako chho
    db = client["crm_ai_setu_mongo"] 
    
    print(f"[MongoDB] Connected to database: {db.name}")

async def close_mongo_connection():
    global client
    if client:
        client.close()
        print("[MongoDB] Connection closed.")

# 2. Aa function ma badlav karo
def get_database():
    global db, client
    if db is not None:
        return db
    if client is not None:
        return client["crm_ai_setu_mongo"]
    return None