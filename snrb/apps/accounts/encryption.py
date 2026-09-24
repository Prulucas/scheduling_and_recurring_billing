"""
Encryption utilities for LGPD compliance.

Provides AES-256-GCM encryption/decryption for PII fields (CPF, phone),
HMAC-SHA256 blind indexes for searchable encrypted data, and utility
functions for masking and validating Brazilian documents.
"""

import base64
import hashlib
import hmac
import os
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.db import models


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------

def get_encryption_key() -> bytes:
    """Read and decode the AES-256 encryption key from environment."""
    key_b64 = os.environ.get('ENCRYPTION_KEY', '')
    if not key_b64:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is not set. "
            "Generate one with generate_encryption_key()."
        )
    key = base64.b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY must be exactly 32 bytes (256 bits).")
    return key


def get_hmac_key() -> bytes:
    """Read and decode the HMAC key from environment."""
    key_b64 = os.environ.get('HMAC_KEY', '')
    if not key_b64:
        raise ValueError(
            "HMAC_KEY environment variable is not set. "
            "Generate one with generate_hmac_key()."
        )
    return base64.b64decode(key_b64)


def generate_encryption_key() -> str:
    """Generate a new random 32-byte AES-256 key, returned as base64."""
    return base64.b64encode(os.urandom(32)).decode('utf-8')


def generate_hmac_key() -> str:
    """Generate a new random 32-byte HMAC key, returned as base64."""
    return base64.b64encode(os.urandom(32)).decode('utf-8')


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------

def encrypt_field(plaintext: str) -> str:
    """
    Encrypt a string using AES-256-GCM.

    Returns a base64-encoded string containing: nonce (12 bytes) + ciphertext + tag.
    A random 12-byte nonce is generated for each call (never reuse nonces).
    """
    if not plaintext:
        return ''

    key = get_encryption_key()
    aesgcm = AESGCM(key)

    nonce = os.urandom(12)  # 96-bit nonce, unique per encryption
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

    # Concatenate nonce + ciphertext (which includes the 16-byte GCM tag)
    encrypted_blob = nonce + ciphertext
    return base64.b64encode(encrypted_blob).decode('utf-8')


def decrypt_field(ciphertext_b64: str) -> str:
    """
    Decrypt a base64-encoded AES-256-GCM ciphertext.

    Expects the format: base64(nonce[12] + ciphertext + tag[16]).
    """
    if not ciphertext_b64:
        return ''

    key = get_encryption_key()
    aesgcm = AESGCM(key)

    encrypted_blob = base64.b64decode(ciphertext_b64)
    nonce = encrypted_blob[:12]
    ciphertext = encrypted_blob[12:]

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


# ---------------------------------------------------------------------------
# HMAC-SHA256 blind index
# ---------------------------------------------------------------------------

def compute_blind_index(value: str) -> str:
    """
    Compute an HMAC-SHA256 blind index for searchable encrypted fields.

    The input is normalized (stripped, digits only for CPF/phone) before
    hashing to ensure deterministic lookups.
    """
    if not value:
        return ''

    key = get_hmac_key()
    normalized = re.sub(r'\D', '', value.strip())
    if not normalized:
        normalized = value.strip().lower()

    digest = hmac.new(key, normalized.encode('utf-8'), hashlib.sha256)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Django custom model field
# ---------------------------------------------------------------------------

class EncryptedCharField(models.CharField):
    """
    A Django CharField that transparently encrypts on save and decrypts on read.

    Data is stored as AES-256-GCM ciphertext (base64) in the database.
    The max_length should account for base64 expansion (~4/3 of plaintext
    plus 12-byte nonce and 16-byte tag overhead).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 512)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt before saving to database."""
        if value is None or value == '':
            return value
        if isinstance(value, str) and not self._is_encrypted(value):
            return encrypt_field(value)
        return value

    def from_db_value(self, value, expression, connection):
        """Decrypt when reading from database."""
        if value is None or value == '':
            return value
        try:
            return decrypt_field(value)
        except Exception:
            # If decryption fails, return raw value (might be unencrypted)
            return value

    def _is_encrypted(self, value: str) -> bool:
        """Heuristic check: valid base64 and reasonable length for encrypted data."""
        try:
            decoded = base64.b64decode(value)
            # Minimum: 12 (nonce) + 16 (tag) + 1 (at least 1 byte data) = 29
            return len(decoded) >= 29
        except Exception:
            return False

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get('max_length') == 512:
            del kwargs['max_length']
        return name, path, args, kwargs


# ---------------------------------------------------------------------------
# Masking utilities
# ---------------------------------------------------------------------------

def mask_cpf(cpf: str) -> str:
    """
    Mask a CPF for display: ***.***.***-XX (last 2 digits visible).

    Accepts formatted (123.456.789-09) or unformatted (12345678909) CPF.
    """
    digits = re.sub(r'\D', '', cpf)
    if len(digits) != 11:
        return '***.***.***-**'
    return f'***.***.***.{digits[-2:]}'


def mask_phone(phone: str) -> str:
    """
    Mask a phone for display: (**) *****-XXXX (last 4 digits visible).

    Accepts various phone formats.
    """
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 4:
        return '(**) *****-****'
    return f'(**) *****-{digits[-4:]}'


# ---------------------------------------------------------------------------
# CPF validation
# ---------------------------------------------------------------------------

def normalize_cpf(cpf: str) -> str:
    """Remove all non-digit characters from CPF."""
    return re.sub(r'\D', '', cpf)


def normalize_phone(phone: str) -> str:
    """Remove all non-digit characters from phone number."""
    return re.sub(r'\D', '', phone)


def validate_cpf(cpf: str) -> bool:
    """
    Validate a Brazilian CPF number by checking its two verification digits.

    Returns True if the CPF is valid, False otherwise.
    """
    digits = normalize_cpf(cpf)

    if len(digits) != 11:
        return False

    # Reject known invalid sequences (all same digits)
    if digits == digits[0] * 11:
        return False

    # First check digit
    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    first_check = 0 if remainder < 2 else 11 - remainder
    if int(digits[9]) != first_check:
        return False

    # Second check digit
    total = sum(int(digits[i]) * (11 - i) for i in range(10))
    remainder = total % 11
    second_check = 0 if remainder < 2 else 11 - remainder
    if int(digits[10]) != second_check:
        return False

    return True
