import sys
sys.path.insert(0, "/app")
from app.db.session import SessionLocal
from app.db.base import Base

db = SessionLocal()
Base.metadata.drop_all(bind=db.get_bind())
Base.metadata.create_all(bind=db.get_bind())
db.close()
print("Clean tables created")
