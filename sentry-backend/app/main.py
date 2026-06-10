from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title=os.getenv("APP_NAME"),
    version=os.getenv("APP_VERSION")
)

@app.get("/")
def root():
    return {
        "message": f"{os.getenv('APP_NAME')} is running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT")
    }