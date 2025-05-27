import datetime

import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.users.routers import router as user_router
from app.products.routers import router as product_router
from app.orders.routers import router as order_router
from app.users.address_router import router as address_router
from app.users.profile_router import router as profile_router
from app.cart.routers import router as cart_router
from app import models, schemas
from app.db import SessionLocal, engine, get_db, init_db
from app.schemas import Greeting
from app.users import models as user_models
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
from app.models import Base
# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
server = FastAPI()

# Add CORS middleware
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Mount static files
# server.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
server.include_router(user_router)
server.include_router(product_router)
server.include_router(order_router)
server.include_router(address_router)
server.include_router(profile_router)
server.include_router(cart_router)

@server.get("/")
async def root():
    return {"message": "Welcome to Silvee API"}

if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8001)
