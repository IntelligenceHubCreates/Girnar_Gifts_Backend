import datetime
import os

import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.users.routers import router as user_router
from app.products.routers import router as product_router, category_router
from app.orders.routers import router as order_router
from app.users.address_router import router as address_router
from app.users.profile_router import router as profile_router
from app.cart.routers import router as cart_router
from app.favorite.routers import router as favorite_router
from app.rating.routers import router as rating_router
from app.newsletter.routers import newsletter_router
from app.coupons.routers import coupon_router
from app import models, schemas
from app.db import SessionLocal, engine, get_db, init_db
from app.schemas import Greeting
from app.users import models as user_models
from fastapi.middleware.cors import CORSMiddleware
from app.admin.routers import admin_router, category_write_router
from app.payments.routers import payment_router
from app.blog.routers import blog_router
from app.admin.analytics_router import analytics_router
from app.returns.routers import returns_router, admin_returns_router
from app.notifications.routers import notifications_router
from app.shipping.routers import (
    admin_shipping_router, admin_couriers_router,
    shipping_router, shiprocket_webhook_router,
)
# from fastapi.staticfiles import StaticFiles
from app.models import Base
# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with comprehensive documentation
server = FastAPI(
    title="Girnar Gifts API",
    description="""
    ## Girnar Gifts E-commerce Platform API

    A comprehensive REST API for the Girnar Gifts e-commerce platform.

    ### Features
    * **User Management** - Authentication, registration, profiles
    * **Product Management** - CRUD operations for gift products
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
    #     "name": "Girnar Gifts Development Team",
    #     "email": "dev@girnargifts.com",
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
    #         "description": "Product management operations for gift items including CRUD operations."
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
    allow_origins=["*"],
    # allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# # Mount static files
# server.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
server.include_router(user_router)
server.include_router(product_router)
server.include_router(category_router)  # add this line
server.include_router(order_router)
server.include_router(address_router)
server.include_router(profile_router)
server.include_router(cart_router)
server.include_router(favorite_router)
server.include_router(rating_router)
server.include_router(admin_router)
server.include_router(category_write_router)
server.include_router(payment_router)
server.include_router(newsletter_router)
server.include_router(coupon_router)  
server.include_router(blog_router)
server.include_router(analytics_router)   # ADD
server.include_router(returns_router)         # customer returns
server.include_router(admin_returns_router)   # admin returns
server.include_router(notifications_router)   # customer notifications (Phase 14)
server.include_router(admin_shipping_router)  # admin shipping
server.include_router(admin_couriers_router)  # admin courier partners
server.include_router(shipping_router)        # customer tracking / my-shipment
server.include_router(shiprocket_webhook_router)  # shiprocket webhook (guarded stub)

@server.get("/")
async def root():
    return {"message": "Welcome to Girnar Gifts API"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    print("PORT", port)
    uvicorn.run(server, host="0.0.0.0", port=port)
