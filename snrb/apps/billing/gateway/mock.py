import threading
import time
import uuid

import requests
from django.conf import settings
from .base import PaymentGatewayBase


class MockGateway(PaymentGatewayBase):
    """
    A mock payment gateway for the Beta MVP.
    It returns fake IDs immediately and fires a delayed "webhook" call locally 
    to simulate async payment confirmation.
    """

    def create_subscription(self, customer_id: int, plan_id: int) -> str:
        return f"mock_sub_{uuid.uuid4().hex[:12]}"

    def cancel_subscription(self, gateway_subscription_id: str) -> bool:
        return True

    def create_charge(self, amount: float, description: str, metadata: dict = None) -> str:
        transaction_id = f"mock_txn_{uuid.uuid4().hex[:12]}"
        
        # Simulate an asynchronous webhook callback in a background thread
        def fire_webhook():
            time.sleep(2)  # Simulate network/processing delay
            webhook_url = 'http://127.0.0.1:8000/api/v1/billing/webhook/'
            payload = {
                'event': 'payment_confirmed',
                'transaction_id': transaction_id,
                'metadata': metadata or {}
            }
            try:
                requests.post(webhook_url, json=payload, timeout=5)
            except Exception as e:
                print(f"[MockGateway] Webhook firing failed: {e}")

        threading.Thread(target=fire_webhook, daemon=True).start()
        
        return transaction_id

    def refund_charge(self, gateway_transaction_id: str) -> str:
        return f"mock_ref_{uuid.uuid4().hex[:12]}"
