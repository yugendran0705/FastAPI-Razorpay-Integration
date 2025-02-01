from typing import Union

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


# from fastapi import FastAPI, HTTPException
# from app.utils import create_plan, create_subscription, cancel_subscription, get_subscription, get_all_plans ,razorpay_client
# from pydantic import BaseModel

# app = FastAPI()

# # In-memory store for subscriptions (Replace with DB for production)
# subscriptions = {}

# # Pydantic model for plan creation input validation
# class PlanCreateRequest(BaseModel):
#     name: str
#     description: str
#     amount: int  # Amount in INR
#     period: str  # 'daily', 'weekly', 'monthly', 'yearly'
#     interval: int  # Interval for the period

# @app.post("/create-plan/")
# def create_new_plan(plan_request: PlanCreateRequest):
#     try:
#         plan = create_plan(
#             name=plan_request.name,
#             description=plan_request.description,
#             amount=plan_request.amount,
#             period=plan_request.period,
#             interval=plan_request.interval
#         )
#         return {"plan": plan}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @app.post("/subscribe/")
# def subscribe(plan_id: str, customer_id: str):
#     try:
#         subscription = create_subscription(plan_id, customer_id)
#         subscriptions[customer_id] = subscription
#         return {"subscription": subscription}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @app.post("/cancel-subscription/")
# def cancel_existing_subscription(customer_id: str):
#     try:
#         subscription = subscriptions.get(customer_id)
#         if not subscription:
#             raise HTTPException(status_code=404, detail="Subscription not found")
#         cancel_subscription(subscription['id'])
#         return {"message": "Subscription cancelled successfully"}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
# @app.get("/customer/{customer_id}/active-plan")
# def get_active_plan(customer_id: str):
#     try:
#         # Fetch all subscriptions
#         subscriptions = razorpay_client.subscription.all()
        
#         if not subscriptions['items']:
#             raise HTTPException(status_code=404, detail="No subscriptions found.")
        
#         # Log all subscriptions to see their details
#         print("Fetched Subscriptions:", subscriptions['items'])
        
#         # Loop through subscriptions and find the active one for the customer_id
#         for subscription in subscriptions['items']:
#             print("Checking subscription:", subscription)  # Log each subscription

#             # Check if the subscription belongs to the customer and is active
#             if subscription['customer_id'] == customer_id and subscription['status'] == 'active':
#                 return {
#                     "subscription_id": subscription['id'],
#                     "plan_id": subscription['plan_id'],
#                     "start_date": subscription['start'],
#                     "end_date": subscription['end'],
#                     "status": subscription['status'],
#                     "amount": subscription['amount']
#                 }
        
#         raise HTTPException(status_code=404, detail="No active subscription found for this customer.")
    
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# # Route to list all available plans
# @app.get("/plans/")
# def list_all_plans():
#     try:
#         plans = get_all_plans()
#         return {"plans": plans}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# # New route to get subscription details by subscription ID
# @app.get("/subscription/{subscription_id}")
# def get_subscription_details(subscription_id: str):
#     try:
#         subscription = get_subscription(subscription_id)
#         return {"subscription": subscription}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @app.get("/")
# def read_root():
#     return {"message": "Welcome to FastAPI Razorpay Subscription Service"}
