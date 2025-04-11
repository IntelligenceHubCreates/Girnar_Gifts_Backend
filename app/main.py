import datetime

import uvicorn
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.users.routers import router as user_router
from app.products.routers import router as product_router
from app.orders.routers import router as order_router
from app.users.address_router import router as address_router
from app import models, schemas
from app.db import SessionLocal, engine, get_db, init_db
from app.schemas import Greeting
from app.users import models as user_models
from fastapi.middleware.cors import CORSMiddleware

server = FastAPI()

server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

server.include_router(user_router)
server.include_router(product_router)
server.include_router(order_router)
server.include_router(address_router)

@server.get("/", response_model=dict)
async def root(db: Session = Depends(get_db)):
    return {'test': 'Hello World', 'list': db.query(models.Greeting).all()}

if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8001)
