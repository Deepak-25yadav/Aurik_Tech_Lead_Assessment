import asyncio
from pathlib import Path
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.session import init_db, async_session_maker
from app.services.seed_service import load_all_seed_data

async def main():
    print("Initializing database tables...")
    await init_db()
    
    print(f"Loading seed data from {settings.DATA_DIR}...")
    async with async_session_maker() as session:
        results = await load_all_seed_data(session, settings.DATA_DIR)
        print("Database seeding completed successfully!")
        for vendor, res in results.items():
            print(f"  • {vendor}: {res}")

if __name__ == "__main__":
    asyncio.run(main())
