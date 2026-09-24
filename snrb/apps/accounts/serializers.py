from django.contrib.auth import get_user_model
from rest_framework import serializers

from .encryption import compute_blind_index, mask_cpf, mask_phone, validate_cpf, normalize_cpf, normalize_phone
from .models import CustomerProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'role')
        read_only_fields = ('role',)


class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    cpf = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = ('id', 'user', 'full_name', 'cpf', 'phone')

    def get_cpf(self, obj):
        # Descriptografa automaticamente pelo model field, mas queremos mascarar para leitura
        return mask_cpf(obj.cpf_encrypted) if obj.cpf_encrypted else None

    def get_phone(self, obj):
        return mask_phone(obj.phone_encrypted) if obj.phone_encrypted else None


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(max_length=255)
    cpf = serializers.CharField(max_length=14)
    phone = serializers.CharField(max_length=20)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Um usuário com este email já existe.")
        return value

    def validate_cpf(self, value):
        if not validate_cpf(value):
            raise serializers.ValidationError("CPF inválido.")
        
        cpf_hash = compute_blind_index(value)
        if CustomerProfile.objects.filter(cpf_hash=cpf_hash).exists():
            raise serializers.ValidationError("Um usuário com este CPF já existe.")
        
        return value

    def validate_phone(self, value):
        phone_hash = compute_blind_index(value)
        if CustomerProfile.objects.filter(phone_hash=phone_hash).exists():
            raise serializers.ValidationError("Um usuário com este telefone já existe.")
        return value

    def create(self, validated_data):
        # 1. Create User
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.Role.CUSTOMER
        )
        
        # 2. Create Profile with Encrypted and Hashed values
        # The EncryptedCharField will handle encryption of cpf/phone automatically on save.
        CustomerProfile.objects.create(
            user=user,
            full_name=validated_data['full_name'],
            cpf_encrypted=normalize_cpf(validated_data['cpf']),
            phone_encrypted=normalize_phone(validated_data['phone']),
            cpf_hash=compute_blind_index(validated_data['cpf']),
            phone_hash=compute_blind_index(validated_data['phone'])
        )
        return user
