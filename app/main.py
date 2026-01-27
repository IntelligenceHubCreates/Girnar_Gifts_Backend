import datetime
import os

import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.users.routers import router as user_router
from app.products.routers import router as product_router
from app.orders.routers import router as order_router
from app.users.address_router import router as address_router
from app.users.profile_router import router as profile_router
from app.cart.routers import router as cart_router
from app.favorite.routers import router as favorite_router
from app import models, schemas
from app.db import SessionLocal, engine, get_db, init_db
from app.schemas import Greeting
from app.users import models as user_models
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
from app.models import Base
# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with comprehensive documentation
server = FastAPI(
    title="Silvee API",
    description="""
    ## Silvee E-commerce Platform API
    
    A comprehensive REST API for the Silvee jewelry e-commerce platform.
    
    ### Features
    * **User Management** - Authentication, registration, profiles
    * **Product Management** - CRUD operations for jewelry products
    * **Order Management** - Shopping cart, checkout, order processing
    * **Payment Integration** - RazorPay payment gateway
    * **Image Management** - Cloudinary integration for product images
    
    ### Authentication
    This API uses JWT tokens for authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```
    
    ### Rate Limiting
    API endpoints are rate-limited to ensure fair usage.
    
    ### Error Handling
    All endpoints return consistent error responses with appropriate HTTP status codes.
    """,
    version="1.0.0",
    # contact={
    #     "name": "Silvee Development Team",
    #     "email": "dev@silvee.com",
    # },
    # license_info={
    #     "name": "MIT",
    #     "url": "https://opensource.org/licenses/MIT",
    # },
    docs_url="/docs",
    redoc_url="/redoc",
    # openapi_url="/openapi.json",
    # openapi_tags=[
    #     {
    #         "name": "users",
    #         "description": "User management operations including authentication, registration, and profile management."
    #     },
    #     {
    #         "name": "products",
    #         "description": "Product management operations for jewelry items including CRUD operations."
    #     },
    #     {
    #         "name": "orders",
    #         "description": "Order management including shopping cart, checkout, and order processing."
    #     },
    #     {
    #         "name": "cart",
    #         "description": "Shopping cart operations for managing items before checkout."
    #     },
    #     {
    #         "name": "payments",
    #         "description": "Payment processing operations including RazorPay integration."
    #     }
    # ]
)

# Add CORS middleware
# Get allowed origins from environment variable, default to localhost for development
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

server.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],
    allow_origins=allowed_origins,
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
server.include_router(favorite_router)

@server.get("/")
async def root():
    return {"message": "Welcome to Silvee API"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(server, host="0.0.0.0", port=port)
