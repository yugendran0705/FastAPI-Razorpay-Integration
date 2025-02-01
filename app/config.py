import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from the .env file

RAZORPAY_API_KEY = os.getenv("RAZORPAY_API_KEY")
RAZORPAY_API_SECRET = os.getenv("RAZORPAY_API_SECRET")

if not RAZORPAY_API_KEY or not RAZORPAY_API_SECRET:
    raise Exception("Razorpay API Key or Secret is missing")
