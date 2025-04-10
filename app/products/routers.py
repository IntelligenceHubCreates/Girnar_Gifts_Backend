import datetime
import json
from typing import List
from uuid import UUID
from app.products.models import Product, ProductBase, ProductIn, ProductListResponse
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.settings import settings
from app.db import get_db
from app.users.models import UserBase, Users
from app.users.utils import JWTBearer
from fastapi import File, UploadFile, Request, Form
import cloudinary
from app.shared.services import upload_images
import cloudinary.uploader

router = APIRouter(prefix= '/api/product')
# router = APIRouter(prefix= '/api/product', dependencies=[Depends(JWTBearer())])

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

@router.get("/", response_model=dict)
async def root(db: Session = Depends(get_db), user = Depends(JWTBearer())):
    print("user", user)
    users = db.query(Users).all()  # Query the users
    user_list = [UserBase.from_orm(user) for user in users]  # Convert to Pydantic models
    return {'test': 'Hello World Test 3', 'list': user_list}

@router.post("/uploadfile/product/{id}", tags=["Product"])
async def upload_product_image(
    id: int,
    file: UploadFile = File(..., max_length=10485760),
    user = Depends(JWTBearer()),
    session: Session = Depends(get_db)
):

    if user is None or user['role'] != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")

    FILEPATH = "./static/images/"
    file_name = file.filename

    # File extension validation
    try:
        extension = file_name.split(".")[1]
    finally:
        if extension not in ["png", "jpg", "jpeg"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="File extension not allowed")

    # Generate a secure token for the file name
    # token_name = "product" + secrets.token_hex(10) + "." + extension
    token_name = "product" + "." + extension
    generated_name = FILEPATH + token_name
    file_content = await file.read()

    # Save the file
    with open(generated_name, "wb") as f:
        f.write(file_content)

    # Retrieve product from the database
    product = session.query(Product).filter(Product.id == id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product Not Found"
        )

    # Assuming the business and owner relationships exist in SQLAlchemy
    business = product.business  # Assuming a relationship exists in the model
    owner = business.owner

    if owner == user:
        # Update product image and save to the database
        product.product_image = generated_name[1:]
        session.commit()  # Commit changes to the database
        
        # Return the updated product using Pydantic schema
        return ProductBase.from_orm(product)  # Converts SQLAlchemy object to Pydantic schema
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
@router.post("", tags=["Product"])
async def add_new_product(
    productName: str = Form(...),
    productCategory: str = Form(...),
    productDescription: str = Form(...),
    productPrice: int = Form(...),
    productCount: int = Form(...),
    productDiscount: int = Form(...),
    productDiscountAmount: int = Form(...),
    productImages: List[UploadFile] = File(...),
    productDetails: List[str] = File(...),
    user = Depends(JWTBearer()),
    session: Session = Depends(get_db)
):
    try:
        if user is None or user['role'] != 1:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")
        
        images = await upload_images(productImages)

        product_data = {
            "original_price": productPrice, 
            "percentage_discount": productDiscount,
            "name": productName,
            "category": productCategory,
            "offer_expiration_date": datetime.datetime(1970, 1, 1),
            "product_image": images,
            "count": productCount,
            "description": productDescription,
            "details": productDetails,
            "amount_discount": productDiscountAmount
        }

        if product_data["original_price"] > 0:
            new_product = Product(**product_data)
            session.add(new_product)
            session.commit()
            session.refresh(new_product)

            return ProductBase.from_orm(
                new_product if not isinstance(new_product.id, UUID) else new_product.__dict__ | {"id": str(new_product.id)}
            )


        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="The original price must be greater than 0")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Something happend ${e}")


@router.delete("/{id}", tags=["Product"])
async def delete_product(
    id: str, 
    user = Depends(JWTBearer()),
    session: Session = Depends(get_db)
):

    if user is None or user['role'] != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")

    product = session.query(Product).filter(Product.id == id).first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    session.delete(product)
    session.commit()
    return {"Message": "Deleted Successfully"}

@router.put("/{id}", tags=["Product"])
async def update_product(
    id: str,
    productName: str = Form(...),
    productCategory: str = Form(...),
    productDescription: str = Form(...),
    productPrice: int = Form(...),
    productCount: int = Form(...),
    productDiscount: int = Form(...),
    productDiscountAmount: int = Form(...),
    productImages: List[UploadFile] = File(None),
    productDetails: List[str] = Form(...),
    oldProductImages = Form(...),
    user=Depends(JWTBearer()),
    session: Session = Depends(get_db)
):
    
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorised")

    product = session.query(Product).filter(Product.id == id).first()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    file_contents = json.loads(oldProductImages)

    if not productImages:
        productImages = []

    images = await upload_images(productImages)

    images.extend(file_contents or [])

    updated_data = {
        "original_price": productPrice, 
        "percentage_discount": productDiscount,
        "name": productName,
        "category": productCategory,
        "product_image": images,
        "count": productCount,
        "description": productDescription,
        "details": productDetails,
        "amount_discount": productDiscountAmount
    }

    if updated_data["original_price"] > 0:
        for key, value in updated_data.items():
            setattr(product, key, value)

        session.commit()
        session.refresh(product)

        product_data = product.__dict__
        product_data["id"] = str(product_data["id"])
        return product_data

    raise HTTPException(
        status_code=status.HTTP_400_UNAUTHORIZED,
        detail="Not authenticated to perform this action or Invalid user input",
        headers={"WWW-Authenticate": "Bearer"}
    )

@router.get("/all", tags=["Product"], response_model=ProductListResponse)
async def get_product_list(limit: int = Query(100, le=100),
                           skip: int = Query(0, ge=0),
                           session: Session = Depends(get_db)):

    products = session.query(Product).offset(skip).limit(limit).all()
    return {
        "data": [
            ProductBase.from_orm(
                product if not isinstance(product.id, UUID) else product.__dict__ | {"id": str(product.id)}
            )
            for product in products
        ],
        "totalCount": len(products),
    }

@router.get("/{id}", tags=["Product"])
async def get_product_detail(id: str, session: Session = Depends(get_db)):
    print("Effort", id)
    product = session.query(Product).filter(Product.id == UUID(id)).first()
    print("JOSH", product)

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    print("Bye", product.__dir__())
    print("Bye12121", product.__dict__)

    product_data = product.__dict__
    # product_data["product_image"] = f'{product_data["product_image"]}'
    product_data["id"] = str(product_data["id"])

    return {
        "product_details": product_data,
    }

