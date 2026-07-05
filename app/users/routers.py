from app.users.services import get_hashed_password, verify_password, handle_google_login
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session
from app import models
from app.db import SessionLocal, get_db
from app.users.models import UserTokens, Users
from app.users.schemas import TokenSchema, UserCreate, requestdetails, GoogleLoginRequest
from app.users.utils import COOKIE_ACCESS_KEY, create_access_token, get_current_user
import httpx
import json
from app.users.utils import JWTBearer

router = APIRouter(prefix='/api/user')


@router.post("/register")
def register_user(user: UserCreate, response: Response, session: Session = Depends(get_db)):
    existing_user = session.query(Users).filter_by(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    encrypted_password = get_hashed_password(user.password)

    new_user = Users(
        name=user.name,
        phone=user.phone,
        email=user.email,
        hashed_password=encrypted_password,
        confirmed=True,
        role=5,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    access = create_access_token(new_user.id, session)

    response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")

    return {"message": "user created successfully", "token": access}


@router.post('/login')
def login(request: requestdetails, response: Response, db: Session = Depends(get_db)):
    user = db.query(Users).filter(Users.email == request.email).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email")
    hashed_pass = user.hashed_password
    if not hashed_pass or not verify_password(request.password, hashed_pass):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    access = create_access_token(user.id, db)

    response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")

    return {
        "user": user,
        "token": access,
        "Message": "Successfully Logged In",
    }


@router.post('/google-login')
def google_login(google_data: GoogleLoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        user = handle_google_login(db, google_data)
        access = create_access_token(user.id, db)

        response.delete_cookie(key=COOKIE_ACCESS_KEY, httponly=True, samesite="strict")
        response.set_cookie(key=COOKIE_ACCESS_KEY, value=access, httponly=True, samesite="strict")

        return {
            "message": "Successfully logged in with Google",
            "token": access,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "phone": user.phone or "",
                "profile_image": user.profile_image or "",
                "confirmed": user.confirmed,
                "role": user.role,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


async def verify_google_token(access_token: str) -> dict:
    """Verify Google access token with Google API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                return response.json()
            return None
    except Exception as e:
        print(f"Error verifying Google token: {e}")
        return None


@router.get('/verify-login')
async def verify_login(request: Request, db: Session = Depends(get_db)):
    """Verify if user is still logged in."""
    try:
        user, error_message = await get_current_user(request, db)
        if not user:
            return {
                "is_logged_in": False,
                "message": error_message or "User not authenticated"
            }

        is_google_user = user.get("google_id") is not None

        google_verified = False
        google_user_info = None

        if is_google_user and user.get("google_access_token"):
            google_user_info = await verify_google_token(user.get("google_access_token"))
            google_verified = google_user_info is not None

            if not google_verified:
                return {
                    "is_logged_in": False,
                    "message": "Google access token expired or invalid",
                    "requires_google_refresh": True
                }

        return {
            "is_logged_in": True,
            "user": {
                "id": user.get("id"),
                "email": user.get("email", ''),
                "name": user.get("name", '') or '',
                "phone": user.get("phone", '') or '',
                "profile_image": user.get("profile_image", '') or '',
                "role": user.get("role", 5),
                "is_google_user": is_google_user,
                "google_verified": google_verified
            },
            "google_info": google_user_info if is_google_user else None,
            "message": "User is authenticated" + (" and Google access verified" if google_verified else "")
        }

    except Exception as e:
        return {
            "is_logged_in": False,
            "message": str(e)
        }


# NOTE: The previous GET '/profile' handler that lived here has been REMOVED.
# It referenced a non-existent `decode_token` import (crashed on every Bearer
# request) and duplicated the route now owned by app/users/profile_router.py,
# which returns the full profile (dob, gender, profile_picture) and is
# header-aware via the fixed get_current_user.


@router.post('/logout')
async def logout(response: Response):
    """Clear access token cookie."""
    response.delete_cookie(key=COOKIE_ACCESS_KEY, httponly=True, samesite="strict")
    return {"message": "Successfully logged out"}


@router.get('/admin/customers')
def admin_get_customers(
    skip: int = 0,
    limit: int = 15,
    segment: str = None,
    search: str = None,
    db: Session = Depends(get_db),
    user=Depends(JWTBearer())
):
    """Paginated customer list (admin only). Returns {data, totalCount}."""
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=401, detail="Unauthorised")

    from sqlalchemy import func as sqlfunc
    from app.orders.models import Order

    query = db.query(
        Users,
        sqlfunc.count(Order.id).label("orders_count"),
        sqlfunc.coalesce(sqlfunc.sum(Order.total_amount), 0).label("total_spent"),
        sqlfunc.max(Order.created_at).label("last_order"),
    ).outerjoin(Order, Users.id == Order.user_id)\
     .filter(Users.role != 1)\
     .group_by(Users.id)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (Users.name.ilike(like)) | (Users.email.ilike(like)) | (Users.phone.ilike(like))
        )

    # Segment filter (mirrors the segment_of logic below)
    if segment and segment.lower() in ("vip", "regular", "new"):
        seg = segment.lower()
        having = sqlfunc.count(Order.id)
        spent  = sqlfunc.coalesce(sqlfunc.sum(Order.total_amount), 0)
        if seg == "vip":
            query = query.having((spent >= 10000) | (having >= 10))
        elif seg == "regular":
            query = query.having((having >= 3) & (having < 10) & (spent < 10000))
        else:  # new
            query = query.having(having < 3)

    # Count distinct customers (subquery so GROUP BY/HAVING are respected)
    total = query.count()

    rows = query.order_by(Users.created_at.desc()).offset(skip).limit(limit).all()

    def segment_of(orders_count, total_spent):
        if float(total_spent) >= 10000 or orders_count >= 10:
            return "vip"
        if orders_count >= 3:
            return "regular"
        return "new"

    return {
        "data": [
            {
                "id":           str(u.id),
                "name":         u.name or "",
                "email":        u.email,
                "phone":        u.phone or "",
                "city":         "",                       # lives on UserAddress; see detail endpoint
                "total_orders": int(oc),
                "total_spent":  float(ts),
                "last_order_date": last.isoformat() if last else None,
                "segment":      segment_of(oc, ts),
                "role":         u.role,
                "is_active":    bool(getattr(u, "is_active", True)),
                "created_at":   u.created_at.isoformat(),
            }
            for u, oc, ts, last in rows
        ],
        "totalCount": total,
    }

@router.get('/admin/customers/{customer_id}')
def admin_get_customer_detail(
    customer_id: str,
    db: Session = Depends(get_db),
    user=Depends(JWTBearer())
):
    """Full customer profile: aggregates + recent orders (by user_id) + addresses."""
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=401, detail="Unauthorised")

    from uuid import UUID
    from sqlalchemy import func as sqlfunc
    from app.orders.models import Order
    from app.users.models import UserAddress

    try:
        uid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    u = db.query(Users).filter(Users.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Aggregates (true totals, independent of the 50-row cap below)
    agg = db.query(
        sqlfunc.count(Order.id),
        sqlfunc.coalesce(sqlfunc.sum(Order.total_amount), 0),
        sqlfunc.max(Order.created_at),
    ).filter(Order.user_id == uid).first()
    total_orders = int(agg[0] or 0)
    total_spent  = float(agg[1] or 0)
    last_order   = agg[2]

    # Recent 50 orders by user_id
    orders = (
        db.query(Order)
        .filter(Order.user_id == uid)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )
    orders_out = [
        {
            "id":           str(o.id),
            "order_number": str(o.id)[:8].upper(),
            "status":       o.status,
            "total_amount": float(o.total_amount or 0),
            "created_at":   o.created_at.isoformat() if o.created_at else None,
            "item_count":   len(o.order_items or []),
        }
        for o in orders
    ]

    # Saved addresses
    addrs = db.query(UserAddress).filter(UserAddress.user_id == uid).all()
    addresses_out = [
        {
            "id":            str(a.id),
            "full_name":     a.full_name,
            "phone":         a.phone,
            "address_line1": a.address_line1,
            "address_line2": a.address_line2 or "",
            "city":          a.city,
            "state":         a.state,
            "postal_code":   a.postal_code,
            "country":       a.country,
            "address_type":  a.address_type,
            "is_default":    bool(a.is_default),
        }
        for a in addrs
    ]

    # Primary city = default address's city (or first address)
    primary_city = ""
    if addresses_out:
        default_addr = next((a for a in addresses_out if a["is_default"]), addresses_out[0])
        primary_city = default_addr["city"]

    return {
        "id":              str(u.id),
        "name":            u.name or "",
        "email":           u.email,
        "phone":           u.phone or "",
        "city":            primary_city,
        "role":            u.role,
        "confirmed":       bool(u.confirmed),
        "is_active":       bool(getattr(u, "is_active", True)),
        "created_at":      u.created_at.isoformat(),
        "profile_image":   getattr(u, "profile_picture", None) or getattr(u, "profile_image", None),
        "total_orders":    total_orders,
        "total_spent":     total_spent,
        "last_order_date": last_order.isoformat() if last_order else None,
        "orders":          orders_out,
        "addresses":       addresses_out,
    }

from pydantic import BaseModel as _PydBase

class _CustomerActivePayload(_PydBase):
    is_active: bool

@router.put('/admin/customers/{customer_id}')
def admin_set_customer_active(
    customer_id: str,
    payload: _CustomerActivePayload,
    db: Session = Depends(get_db),
    user=Depends(JWTBearer())
):
    """Toggle a customer's active flag (admin only)."""
    if user is None or user['role'] != 1:
        raise HTTPException(status_code=401, detail="Unauthorised")

    from uuid import UUID
    try:
        uid = UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID")

    u = db.query(Users).filter(Users.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="Customer not found")
    if u.role == 1:
        raise HTTPException(status_code=400, detail="Cannot change an admin's status")

    u.is_active = payload.is_active
    db.commit()
    return {"id": str(u.id), "is_active": u.is_active}