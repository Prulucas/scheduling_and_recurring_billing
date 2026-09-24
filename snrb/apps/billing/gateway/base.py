from abc import ABC, abstractmethod


class PaymentGatewayBase(ABC):
    """
    Abstract interface for payment gateways (Stripe, Asaas, Mercado Pago, Mock).
    """

    @abstractmethod
    def create_subscription(self, customer_id: int, plan_id: int) -> str:
        """
        Creates a recurring subscription in the gateway.
        Returns the gateway's subscription ID.
        """
        pass

    @abstractmethod
    def cancel_subscription(self, gateway_subscription_id: str) -> bool:
        """
        Cancels an active subscription.
        Returns True if successful.
        """
        pass

    @abstractmethod
    def create_charge(self, amount: float, description: str, metadata: dict = None) -> str:
        """
        Creates a single charge (e.g. 10% reservation fee).
        Returns the gateway's transaction ID.
        """
        pass

    @abstractmethod
    def refund_charge(self, gateway_transaction_id: str) -> str:
        """
        Refunds a specific transaction.
        Returns the gateway's refund ID.
        """
        pass
