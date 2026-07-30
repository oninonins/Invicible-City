import sqlalchemy as sa

engine = sa.create_engine("postgresql://postgres:password@sdgs-db-1:5432/sdgs")
conn = engine.connect()
result = conn.execute(sa.text("SELECT PostGIS_Version()")).scalar()
print(f"PostGIS: {result}")
conn.close()
print("DB connection from container OK")
