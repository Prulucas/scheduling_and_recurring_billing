from django.urls import path
from .views import BarberListView, BarberDetailView, ServiceListView, AvailableSlotsView

urlpatterns = [
    path('barbers/', BarberListView.as_view(), name='barber-list'),
    path('barbers/<int:pk>/', BarberDetailView.as_view(), name='barber-detail'),
    path('barbers/<int:pk>/available-slots/', AvailableSlotsView.as_view(), name='available-slots'),
    path('services/', ServiceListView.as_view(), name='service-list'),
]
