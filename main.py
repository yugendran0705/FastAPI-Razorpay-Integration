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
import os
import hmac
import hashlib


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

app = FastAPI()
# Database setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*","http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
