from django.urls import path
from .views import PlanListView, SubscriptionView
from .webhooks import WebhookView

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('subscriptions/me/', SubscriptionView.as_view(), name='subscription-me'),
    path('billing/webhook/', WebhookView.as_view(), name='billing-webhook'),
]
