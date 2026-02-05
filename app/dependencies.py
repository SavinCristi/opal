
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status

from app.database.database import get_db_session

token_auth_scheme = HTTPBearer()

#async def authenticate(token: str = Depends(token_auth_scheme)) -> str:
#    return token.credentials

class User(BaseModel):
    email: str

async def authenticate(token = Depends(token_auth_scheme)) -> User:
    token_str = token.credentials

    # Since the token is now just the email, return it directly
    if "@" not in token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid format (should be an email)"
        )

    return User(email=token_str)


DBSessionDep = Depends(get_db_session)
