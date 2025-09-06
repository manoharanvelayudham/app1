from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TYPE_CHECKING, Callable
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import UserRole  # Added direct import for UserRole

# Lazy import to avoid circular imports
if TYPE_CHECKING:
    from app.models import User

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# Pydantic models for requests/responses
class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: int
    role: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserInfo(BaseModel):
    id: int
    email: str
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

# JWT utilities
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if token type matches
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check expiration
        if datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

# Authentication functions
async def authenticate_user(db: Session, email: str, password: str) -> 'Optional[User]':
    """Authenticate user by email and password."""
    from app.models import User  # Local import to avoid circular imports
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

async def login_user(db: Session, email: str, password: str) -> 'Dict[str, Any]':
    """Login user and return tokens."""
    user = await authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "user_id": user.id,
        "role": user.role.value
    }

async def refresh_access_token(db: Session, refresh_token: str) -> 'Dict[str, Any]':
    """Refresh access token using refresh token."""
    from app.models import User  # Local import to avoid circular imports
    
    payload = verify_token(refresh_token, "refresh")
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "user_id": user.id,
        "role": user.role.value
    }

# Dependencies for protected routes
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> 'User':
    """Get current authenticated user."""
    from app.models import User  # Local import to avoid circular imports
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = verify_token(token, "access")
        if not payload:
            raise credentials_exception
            
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None or role is None:
            raise credentials_exception
            
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise credentials_exception
            
        return user
    except JWTError:
        raise credentials_exception

async def get_current_active_user(current_user: 'User' = Depends(get_current_user)) -> 'User':
    """Get current active user."""
    return current_user

# Role-based access control
def require_role(required_role: UserRole) -> 'Callable[[User], User]':
    """Dependency factory for role-based access control."""
    async def role_checker(current_user: 'User' = Depends(get_current_active_user)) -> 'User':
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role.value} role"
            )
        return current_user
    return role_checker

def require_any_role(*allowed_roles: UserRole) -> 'Callable[[User], User]':
    """Dependency factory for multiple allowed roles."""
    async def role_checker(current_user: 'User' = Depends(get_current_active_user)) -> 'User':
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of these roles: {', '.join(r.value for r in allowed_roles)}"
            )
        return current_user
    return role_checker

# Common role dependencies
require_admin = require_role(UserRole.ADMIN)
require_trainer = require_role(UserRole.TRAINER)
require_client = require_role(UserRole.CLIENT)

# Multiple role dependencies
require_admin_or_trainer = require_any_role(UserRole.ADMIN, UserRole.TRAINER)
require_any_authenticated = get_current_user

# Utility functions
def user_can_access_user_data(current_user: 'User', target_user_id: int) -> bool:
    """Check if user can access another user's data."""
    # Admins can access any user's data
    if current_user.role == UserRole.ADMIN:
        return True
    
    # Users can only access their own data
    return current_user.id == target_user_id

def user_can_modify_user_data(current_user: 'User', target_user_id: int) -> bool:
    """Check if user can modify another user's data."""
    # Admins can modify any user's data
    if current_user.role == UserRole.ADMIN:
        return True
    
    # Users can only modify their own data
    return current_user.id == target_user_id