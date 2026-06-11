from pydantic import BaseModel
from app.auth.jwt import create_access_token
from app.auth.password import verify_password

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    password: str

def authenticate_user(email: str, password: str, hashed_password: str) -> bool:
    return verify_password(password, hashed_password)

def generate_token(user_id: str) -> Token:
    token = create_access_token(data={"sub": user_id})
    return Token(access_token=token, token_type="bearer")