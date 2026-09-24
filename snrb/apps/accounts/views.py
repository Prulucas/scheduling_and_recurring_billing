from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .encryption import compute_blind_index
from .models import CustomerProfile
from .serializers import CustomerProfileSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Endpoint to register a new Customer.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Return the created profile data
        profile = user.customer_profile
        profile_serializer = CustomerProfileSerializer(profile)
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint to view and update the logged-in customer's profile.
    """
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CustomerProfileSerializer

    def get_object(self):
        # Assumes user is a CUSTOMER and has a profile
        return self.request.user.customer_profile


class SearchByDocumentView(generics.ListAPIView):
    """
    Admin-only endpoint to search for a customer by exact CPF or phone using blind indexes.
    """
    permission_classes = (permissions.IsAuthenticated, permissions.IsAdminUser)
    serializer_class = CustomerProfileSerializer

    def get_queryset(self):
        cpf = self.request.query_params.get('cpf')
        phone = self.request.query_params.get('phone')
        
        queryset = CustomerProfile.objects.all()
        
        if cpf:
            cpf_hash = compute_blind_index(cpf)
            queryset = queryset.filter(cpf_hash=cpf_hash)
            
        if phone:
            phone_hash = compute_blind_index(phone)
            queryset = queryset.filter(phone_hash=phone_hash)
            
        return queryset
