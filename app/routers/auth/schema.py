
from typing import Optional
from pydantic import BaseModel, EmailStr

##### User Schema #####

class UserBase(BaseModel):
    email: EmailStr
    name: str
    country: Optional[str] = None
    organisation: Optional[str] = None
    position: Optional[str] = None
    authority: Optional[str] = None
    SSM_functions: Optional[str] = None
    isSSM: Optional[bool] = None
    org_unit_level_a: Optional[str] = None
    team: Optional[str] = None
    engagement_ids: Optional[str] = None
    
    
class UserCreateRequest(UserBase):
    password: str

class User(UserBase):
    class Config:
        from_attributes = True

class UserSignInRequest(BaseModel):
    email: EmailStr
    password: str


class UserSignInResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

