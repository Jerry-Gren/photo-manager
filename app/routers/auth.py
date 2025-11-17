"""
API router for authentication-related endpoints.

Includes routes for user registration, login (token issuance),
token refresh, logout, and a protected endpoint for user profile retrieval.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Response 
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Handles new user registration.

    Checks for existing username and email before creating a new user.

    Args:
        user: The user creation schema containing username, email, and password.
        db: The database session dependency.

    Returns:
        The newly created user's data (as per schemas.User).

    Raises:
        HTTPException (400): If the username or email is already registered.
    """
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_email = crud.get_user_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.password)
    
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    return crud.create_user(db=db, user=db_user)

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    response: Response, 
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
    db: Session = Depends(get_db)
):
    """
    Logs in a user using OAuth2 username/password form.

    On successful login, it returns an access token in the response body
    and sets a long-lived refresh token in an HttpOnly cookie.

    Args:
        response: The FastAPI Response object (injected) to set the cookie.
        form_data: The OAuth2PasswordRequestForm (username, password).
        db: The database session dependency.

    Returns:
        A Token schema containing the access_token and token_type.

    Raises:
        HTTPException (401): If authentication fails (incorrect username/password).
    """
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(
        data={"sub": user.username}
    )
    
    refresh_token = auth.create_refresh_token(
        data={"sub": user.username}
    )

    # Set the refresh token in an HttpOnly cookie for security
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,            # JS cannot read this cookie
        samesite="strict",        # Strict cross-site policy
        secure=False,             # Set to True in production (requires HTTPS)
        # path="/api/v1/auth"     # Limit cookie path
    )
    
    # Return only the access token in the response body
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=schemas.Token)
async def refresh_access_token(
    current_user: Annotated[models.User, Depends(auth.get_current_user_from_refresh_token)]
):
    """
    Refreshes the access token using the refresh token from the cookie.

    This endpoint is protected by the 'get_current_user_from_refresh_token'
    dependency, which validates the 'refresh_token' cookie.

    Args:
        current_user: The user model instance, injected by the dependency
                      if the refresh token is valid.

    Returns:
        A new access token in a Token schema.
    """
    # The dependency 'get_current_user_from_refresh_token' has already
    # validated the refresh token and provided the user.
    
    # Optional: Implement refresh token rotation here (as per design spec)
    # 1. Create a new refresh_token.
    # 2. Set the new token in the response cookie.
    # 3. Add the old refresh_token (or its JTI) to a denylist.
    # For now, we are just re-issuing the access token.
    
    access_token = auth.create_access_token(
        data={"sub": current_user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """
    Logs the user out by clearing the refresh_token cookie.

    Args:
        response: The FastAPI Response object (injected) to delete the cookie.

    Returns:
        A message confirming successful logout.
    """
    response.delete_cookie(key="refresh_token", httponly=True, samesite="strict")
    return {"message": "Logout successful"}


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[models.User, Depends(auth.get_current_active_user)]
):
    """
    Gets the profile for the currently authenticated user.

    This endpoint is protected by the 'get_current_active_user' dependency,
    which validates the 'Authorization: Bearer' access token.

    Args:
        current_user: The authenticated user model, injected by the
                      'get_current_active_user' dependency.

    Returns:
        The current user's profile data (as per schemas.User).
    """
    return current_user