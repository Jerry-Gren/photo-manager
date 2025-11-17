"""
Authentication utilities for the FastAPI application.

Handles user authentication, password hashing, and JWT token creation/validation.
"""

import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import get_db

# JWT configuration and environment variables
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored hash.

    Args:
        plain_password: The plain-text password to check.
        hashed_password: The stored hashed password.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt.

    Args:
        password: The plain-text password to hash.

    Returns:
        The resulting password hash as a string.
    """
    return pwd_context.hash(password)

# JWT Token creation
def create_access_token(data: dict) -> str:
    """
    Creates a new JWT access token with a short expiry.

    Args:
        data: The data to encode in the token (e.g., {'sub': username}).

    Returns:
        The encoded JWT access token as a string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """
    Creates a new JWT refresh token with a long expiry.

    Args:
        data: The data to encode in the token (e.g., {'sub': username}).

    Returns:
        The encoded JWT refresh token as a string.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Authentication dependencies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

credentials_exception_cookie = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate refresh token",
)

def get_current_user_from_refresh_token(
    request: Request, 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency to get the current user from the 'refresh_token' cookie.

    Used primarily for the token refresh endpoint.

    Args:
        request: The FastAPI Request object (to access cookies).
        db: The database session dependency.

    Returns:
        The authenticated User model instance.

    Raises:
        HTTPException (401): If the refresh token is missing, invalid,
            expired, or the user does not exist.
    """
    token = request.cookies.get("refresh_token")
    if token is None:
        raise credentials_exception_cookie
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception_cookie
        token_data = schemas.TokenData(sub=username)
    except JWTError:
        raise credentials_exception_cookie
    
    user = crud.get_user_by_username(db, username=token_data.sub)
    if user is None:
        raise credentials_exception_cookie
    return user


# User authentication logic
def authenticate_user(db: Session, username: str, password: str) -> models.User | bool:
    """
    Validates a user's username and password.

    Args:
        db: The database session.
        username: The user's username.
        password: The user's plain-text password.

    Returns:
        The authenticated User model instance if credentials are correct,
        False otherwise.
    """
    user = crud.get_user_by_username(db, username=username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Validates the JWT access token and retrieves the current user.

    This is a dependency function injected into protected endpoints.

    Args:
        token: The OAuth2 bearer token provided in the Authorization header.
        db: The database session dependency.

    Returns:
        The authenticated User model instance if the token is valid
        and the user exists.

    Raises:
        HTTPException (401): If the token is invalid, expired,
            or the user associated with the token does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(sub=username)
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_username(db, username=token_data.sub)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User:
    """
    A dependency that ensures the user is active.

    (Currently, it just returns the user, but it's a placeholder
    for future logic, e.g., checking an 'is_active' flag.)

    Args:
        current_user: The user object obtained from `get_current_user`.

    Returns:
        The active User model instance.
    """
    # In the future, add:
    # if not current_user.is_active:
    #    raise HTTPException(status_code=400, detail="Inactive user")
    return current_user