from typing import Union
# Import necessary modules and classes
import httpx
import requests
from fastapi import FastAPI, Depends, HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String
import sqlalchemy
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from dotenv import load_dotenv
import datetime
import os
import hmac
import hashlib
import razorpay


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

app = FastAPI()
# Database setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = sqlalchemy.orm.declarative_base()

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    amount = Column(Integer)
    currency = Column(String)
    status = Column(String)
    username = Column(String)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True, index=True)
    plan_id = Column(String)
    plan_name = Column(String)
    plan_amount = Column(Integer)
    plan_currency = Column(String)
    status = Column(String)
    username = Column(String)
    created_at = Column(String)
    expires_at = Column(String)
    payment_id = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    email = Column(String)
    contact = Column(String)
    customer_id = Column(String)
    subscription_id = Column(String)



class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

# Create a separate Pydantic model for input validation
class PaymentCreate(BaseModel):
    amount: int
    currency: str
    username: str
    status: str

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_signature(request_body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature"""
    generated_signature = hmac.new(
        bytes(RAZORPAY_WEBHOOK_SECRET, 'utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(generated_signature, signature)

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/payment/")
def create_purchase(payment: PaymentCreate, db: Session = Depends(get_db)):
    try:
        response = requests.post(
            "https://api.razorpay.com/v1/orders",
            json={
                "amount": payment.amount,
                "currency": payment.currency,
            },
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )
        response.raise_for_status()
        order_data = response.json()

        db_payment = Payment(
            id=order_data['id'],
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            username=payment.username
        )
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        return db_payment
    except requests.HTTPError as e:
        print(e)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/payment/verify")
async def verify_payment(paymentVerify: PaymentVerify, db: Session = Depends(get_db)):
    try:
        message = f"{paymentVerify.razorpay_order_id}|{paymentVerify.razorpay_payment_id}".encode('utf-8')
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg=message,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, paymentVerify.razorpay_signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

        payment = db.query(Payment).filter(Payment.id == paymentVerify.razorpay_order_id).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        payment.status = "paid"
        db.commit()
        db.refresh(payment)

        return {
            "status": "success",
            "payment_id": payment.id,
            "amount": payment.amount,
            "currency": payment.currency
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error verifying payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during verification")

@app.post("/payment/failure/{order_id}")
async def payment_failure(
    db: Session = Depends(get_db),
    order_id: str = None
):
    try:
        print(order_id)
        payment = db.query(Payment).filter(Payment.id == order_id).first()
        if payment:
            payment.status = "failed"
            db.commit()
            db.refresh(payment)

            return {
                "message":"Payment failed",
                "payment_id": payment.id,
                "amount": payment.amount,
            }
        else:
            raise HTTPException(status_code=404, detail = "No payments found")
    except Exception as e:
        db.rollback()
        print(f"Error verifying payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error during verification")


@app.get("/plans")
async def get_plans():
    try:
        response = requests.get(
            "https://api.razorpay.com/v1/plans",
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print(e)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/subscription/{plan_id}/{username}")
async def create_subscription(
    db: Session = Depends(get_db),
    plan_id: str = None,
    username: str = None
):
    print(plan_id)
    print(username)
    try:
        if not plan_id:
            raise HTTPException(status_code=400, detail="Plan ID is required")
        response = requests.get(
                f"https://api.razorpay.com/v1/plans/{plan_id}",
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
        response.raise_for_status()
        plan_data = response.json()
        print(plan_data)
        customer_details = db.query(User).filter(User.username == username).first()
        if not customer_details.customer_id:
            response = requests.post(
                "https://api.razorpay.com/v1/customers",
                json={
                    "name": username, 
                    "email": f"{username}@example.com",
                    "contact": "+919876543210",
                },
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
            response.raise_for_status()
            customer_data = response.json()
            customer_id = customer_data["id"]
            customer_details.customer_id = customer_id
            db.commit()
        else:
            customer_id = customer_details.customer_id

        response = requests.post(
            "https://api.razorpay.com/v1/subscriptions",
            json={
                "plan_id": plan_data["id"],
                "customer_notify": 1,
                "notes": {"username": username},
                "total_count": 12,
                "quantity": 1,
                "start_at": int((datetime.datetime.now() + datetime.timedelta(hours=1)).timestamp()),
                "customer_id": customer_id
            },
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )
        response.raise_for_status()
        subscription_data = response.json()
        print(subscription_data)
        db_subscription = Subscription(
            plan_id=subscription_data["plan_id"],
            plan_name=plan_data["item"]["name"],
            plan_amount=plan_data["item"]["amount"],
            plan_currency=plan_data["item"]["currency"],
            status=subscription_data["status"],
            username=username,
            created_at=subscription_data["created_at"],
            expires_at=subscription_data["current_start"],
            id=subscription_data["id"]
        )
        db.add(db_subscription)
        db.commit()
        db.refresh(db_subscription)
        return subscription_data

    except requests.HTTPError as e:
        print(e)
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def razorpay_webhook(request: Request):
    print("here")
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature or not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Unauthorized: Signature verification failed")

    data = await request.json()
    event = data.get("event")

    if event == "subscription.activated":
        print("Subscription activated:", data)
    elif event == "subscription.charged":
        print("Subscription renewed:", data)
    elif event == "subscription.halted":
        print("Subscription payment failed:", data)
    elif event == "subscription.expired":
        print("Subscription expired:", data)
    elif event == "subscription.created":
        print("Subscription created:", data)
    elif event == "subscription.authenticated":
        print("Subscription authenticated:", data)
    elif event == "payment.authorized":
        print("Payment authorized:", data)
        user_details = db.query(User).filter(User.username == data["payload"]["payment"]["entity"]["customer_id"]).first()
        sub_details = db.query(Subscription).filter(Subscription.id == data["subscription_id"]).first()
        if sub_details:
            sub_details.status = "active"
            sub_details.expires_at = data["current_end"]
            user_details.subscription_id = data["subscription_id"]
            db.commit()
            db.refresh(sub_details)
            db.refresh(user_details)
    else:
        print("Other event received:", data)

    return {"status": "ok"}