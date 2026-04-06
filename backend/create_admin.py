import sys
import os

# Add the current directory to sys.path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.db_models import User
from auth.handlers import hash_password

def create_admin():
    db = SessionLocal()
    email = "admin@bonequest.com"
    
    # Check if admin already exists
    admin_user = db.query(User).filter(User.email == email).first()
    if admin_user:
        print(f"✅ Admin user already exists: {email}")
        return

    # Create new admin
    new_admin = User(
        email=email,
        password_hash=hash_password("admin123"),
        full_name="System Administrator",
        role="admin",
        is_active=True
    )
    
    db.add(new_admin)
    db.commit()
    print(f"🚀 Admin user successfully created!")
    print(f"   Email: {email}")
    print(f"   Password: admin123")

if __name__ == "__main__":
    create_admin()
