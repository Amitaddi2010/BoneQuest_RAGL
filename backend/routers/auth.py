# ============================================================
# BoneQuest v2 — Auth Router
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
from models.schemas import SignUpRequest, SignInRequest, TokenResponse, UserResponse, RefreshTokenRequest, UserUpdateRequest
from auth.handlers import signup_user, signin_user, hash_password
from auth.jwt_utils import decode_token, create_access_token, blacklist_token
from auth.permissions import get_current_user
from models.db_models import User, AuditLog

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignUpRequest, req: Request, db: Session = Depends(get_db)):
    """Register a new user account."""
    result = await signup_user(request, db)

    # Audit log
    audit = AuditLog(
        user_id=result.user.id,
        action="signup",
        resource_type="user",
        resource_id=result.user.id,
        details={"role": request.role.value, "hospital_id": request.hospital_id},
        ip_address=req.client.host if req.client else None,
    )
    db.add(audit)
    db.commit()

    return result


@router.post("/signin", response_model=TokenResponse)
async def signin(request: SignInRequest, req: Request, db: Session = Depends(get_db)):
    """Authenticate and receive tokens."""
    result = await signin_user(request, db)

    # Audit log
    audit = AuditLog(
        user_id=result.user.id,
        action="signin",
        resource_type="user",
        resource_id=result.user.id,
        ip_address=req.client.host if req.client else None,
    )
    db.add(audit)
    db.commit()

    return result


@router.post("/logout")
async def logout(req: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout and invalidate token."""
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        blacklist_token(token)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="logout",
        resource_type="user",
        resource_id=user.id,
        ip_address=req.client.host if req.client else None,
    )
    db.add(audit)
    db.commit()

    return {"message": "Logged out successfully"}


@router.post("/refresh-token", response_model=dict)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Get a new access token using a refresh token."""
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token({"sub": user.id, "role": user.role, "email": user.email})
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        hospital_id=user.hospital_id,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    req: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile info."""
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.hospital_id is not None:
        user.hospital_id = request.hospital_id
    if request.email is not None:
        # Check if email is available
        existing = db.query(User).filter(User.email == request.email, User.id != user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = request.email
    
    if request.password is not None:
        user.password_hash = hash_password(request.password)
    
    db.commit()
    db.refresh(user)

    # Audit log
    audit = AuditLog(
        user_id=user.id,
        action="update_profile",
        resource_type="user",
        resource_id=user.id,
        ip_address=req.client.host if req.client else None,
    )
    db.add(audit)
    db.commit()

    return user
