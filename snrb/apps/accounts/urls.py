from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import ProfileView, RegisterView, SearchByDocumentView

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile & Search
    path('profile/', ProfileView.as_view(), name='profile'),
    path('search/', SearchByDocumentView.as_view(), name='search_by_document'),
]
