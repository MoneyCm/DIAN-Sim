import sqlite3
import bcrypt

try:
    conn = sqlite3.connect('dian_sim.db')
    c = conn.cursor()
    
    # Check if test user exists
    c.execute("SELECT id FROM users WHERE username='testuser'")
    if c.fetchone():
        print("User 'testuser' already exists.")
    else:
        # Create test user
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw('password123'.encode(), salt).decode()
        c.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)", ('testuser', hashed, 'user'))
        conn.commit()
        print("User 'testuser' created successfully.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
