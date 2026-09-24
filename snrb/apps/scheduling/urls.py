from django.urls import path
from .views import (
    AppointmentListView, 
    CreateAppointmentView, 
    CancelAppointmentView,
    ApproveRefundView,
    NoShowView,
    CompleteAppointmentView
)

urlpatterns = [
    path('appointments/', AppointmentListView.as_view(), name='appointment-list'),
    path('appointments/create/', CreateAppointmentView.as_view(), name='appointment-create'),
    path('appointments/<int:pk>/cancel/', CancelAppointmentView.as_view(), name='appointment-cancel'),
    
    # Barber only actions
    path('appointments/<int:pk>/approve-refund/', ApproveRefundView.as_view(), name='appointment-approve-refund'),
    path('appointments/<int:pk>/no-show/', NoShowView.as_view(), name='appointment-no-show'),
    path('appointments/<int:pk>/complete/', CompleteAppointmentView.as_view(), name='appointment-complete'),
]
