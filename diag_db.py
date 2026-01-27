import os
import streamlit as st

print("--- Diagnostic: DB Connection ---")
db_url_env = os.getenv("DATABASE_URL")
print(f"Environment DATABASE_URL: {db_url_env}")

try:
    db_url_secrets = st.secrets.get("DATABASE_URL")
    print(f"Streamlit Secrets DATABASE_URL: {db_url_secrets}")
except Exception as e:
    print(f"Streamlit Secrets Error: {e}")

# Check for .env file existence again
env_exists = os.path.exists(".env")
print(f".env file exists in current directory? {env_exists}")

# Check parent directory
parent_env_exists = os.path.exists("../.env")
print(f".env file exists in parent directory? {parent_env_exists}")
