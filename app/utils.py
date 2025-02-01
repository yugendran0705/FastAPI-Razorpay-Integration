import razorpay
from app.config import RAZORPAY_API_KEY, RAZORPAY_API_SECRET

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(RAZORPAY_API_KEY, RAZORPAY_API_SECRET))

def create_plan(name: str, description: str, amount: int, period: str, interval: int):
    plan_data = {
        "period": period,
        "interval": interval,
        "item": {
            "name": name,
            "amount": amount * 100,  # Razorpay expects amount in paise
            "currency": "INR",
            "description": description
        }
    }
    plan = razorpay_client.plan.create(plan_data)
    return plan

def create_subscription(plan_id: str, customer_id: str):
    subscription_data = {
        "plan_id": plan_id,
        "customer_notify": 1,
        "total_count": 7,  # For 7 days
        "quantity": 1
        # u can add offers also
    }
    subscription = razorpay_client.subscription.create(subscription_data)
    return subscription

def cancel_subscription(subscription_id: str):
    razorpay_client.subscription.cancel(subscription_id)

# New function to list all available plans
def get_all_plans():
    plans = razorpay_client.plan.all()
    return plans

def get_subscription(subscription_id: str):
    subscription = razorpay_client.subscription.fetch(subscription_id)
    return subscription