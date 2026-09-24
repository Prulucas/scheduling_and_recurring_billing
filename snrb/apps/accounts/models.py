from django.contrib.auth.models import AbstractUser
from django.db import models

from .encryption import EncryptedCharField
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        BARBER = 'BARBER', 'Barber'
        ADMIN = 'ADMIN', 'Admin'

    # Remove username field and use email as unique identifier
    username = None
    email = models.EmailField(unique=True, verbose_name="Email Address")

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        limit_choices_to={'role': CustomUser.Role.CUSTOMER}
    )
    full_name = models.CharField(max_length=255)

    # LGPD Encrypted Fields (AES-256-GCM)
    cpf_encrypted = EncryptedCharField(max_length=512, blank=True, null=True)
    phone_encrypted = EncryptedCharField(max_length=512, blank=True, null=True)

    # Blind Index Hashes for searchability (HMAC-SHA256)
    cpf_hash = models.CharField(max_length=64, blank=True, null=True, unique=True, db_index=True)
    phone_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)

    def __str__(self):
        return f"Customer: {self.full_name}"
