from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan, Subscription
from .serializers import PlanSerializer, SubscriptionSerializer
from .gateway.factory import get_payment_gateway


class PlanListView(generics.ListAPIView):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = (permissions.AllowAny,)


class SubscriptionView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        """Get the current user's subscription."""
        customer = request.user.customer_profile
        subscription = Subscription.objects.filter(
            customer=customer, 
            status=Subscription.Status.ACTIVE
        ).first()
        
        if not subscription:
            return Response({"detail": "No active subscription."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def post(self, request):
        """Create a new subscription."""
        customer = request.user.customer_profile
        plan_id = request.data.get('plan_id')
        
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Check if already has active subscription
        if Subscription.objects.filter(customer=customer, status=Subscription.Status.ACTIVE).exists():
            return Response({"error": "You already have an active subscription."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Integration with Gateway
        gateway = get_payment_gateway()
        try:
            gw_sub_id = gateway.create_subscription(customer.id, plan.id)
        except Exception as e:
            return Response({"error": f"Gateway error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        now = timezone.now()
        sub = Subscription.objects.create(
            customer=customer,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),  # Simplified for monthly
            gateway_subscription_id=gw_sub_id
        )
        
        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        """Cancel subscription."""
        customer = request.user.customer_profile
        subscription = Subscription.objects.filter(
            customer=customer, 
            status=Subscription.Status.ACTIVE
        ).first()
        
        if not subscription:
            return Response({"error": "No active subscription to cancel."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Call gateway
        gateway = get_payment_gateway()
        gateway.cancel_subscription(subscription.gateway_subscription_id)
        
        subscription.status = Subscription.Status.CANCELED
        subscription.save()
        
        return Response({"detail": "Subscription canceled successfully."}, status=status.HTTP_200_OK)
