from django.conf import settings
from .mock import MockGateway


def get_payment_gateway():
    """
    Factory function to return the configured payment gateway instance.
    """
    gateway_name = getattr(settings, 'PAYMENT_GATEWAY', 'mock').lower()
    
    if gateway_name == 'mock':
        return MockGateway()
    # elif gateway_name == 'stripe':
    #     from .stripe import StripeGateway
    #     return StripeGateway()
    
    return MockGateway()
