from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dian_sim.db"))
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

def check_schema():
    print(f"Inspecting DB at: {db_path}")
    if "user_stats" in inspector.get_table_names():
        print("Table 'user_stats' exists. Columns:")
        columns = inspector.get_columns("user_stats")
        for col in columns:
            print(f" - {col['name']} ({col['type']})")
    else:
        print("Table 'user_stats' DOES NOT EXIST.")

if __name__ == "__main__":
    check_schema()
