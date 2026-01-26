import hashlib
import os
import streamlit as st
from sqlalchemy.orm import Session
from db.models import User
from db.session import SessionLocal

class AuthManager:
    @staticmethod
    def hash_password(password: str) -> str:
        # Simple SHA256 hashing for the MVP, could use werkzeug or bcrypt if available
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return AuthManager.hash_password(password) == hashed_password

    @staticmethod
    def login(username, password):
        db = SessionLocal()
        user = db.query(User).filter(User.username == username).first()
        db.close()
        
        if user and AuthManager.verify_password(password, user.password_hash):
            st.session_state["logged_in"] = True
            st.session_state["user_id"] = user.id
            st.session_state["username"] = user.username
            st.session_state["user_role"] = user.role
            return True
        return False

    @staticmethod
    def logout():
        st.session_state["logged_in"] = False
        st.session_state["user_id"] = None
        st.session_state["username"] = None
        st.session_state["user_role"] = None
        st.rerun()

    @staticmethod
    def check_auth():
        if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
            return False
        return True
