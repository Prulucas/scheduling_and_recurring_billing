"""
Tests for the encryption module (LGPD compliance).

Covers AES-256-GCM encrypt/decrypt, HMAC-SHA256 blind indexes,
CPF validation, and masking utilities.
"""

import base64
import os
import unittest

# Set test keys before importing the module
os.environ['ENCRYPTION_KEY'] = base64.b64encode(os.urandom(32)).decode()
os.environ['HMAC_KEY'] = base64.b64encode(os.urandom(32)).decode()

from apps.accounts.encryption import (
    compute_blind_index,
    decrypt_field,
    encrypt_field,
    generate_encryption_key,
    generate_hmac_key,
    mask_cpf,
    mask_phone,
    normalize_cpf,
    normalize_phone,
    validate_cpf,
)


class TestAES256GCMEncryption(unittest.TestCase):
    """Tests for AES-256-GCM encrypt/decrypt round-trip."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting should return the original plaintext."""
        plaintext = "12345678909"
        encrypted = encrypt_field(plaintext)
        decrypted = decrypt_field(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_decrypt_unicode(self):
        """Should handle Unicode characters (accented names, etc.)."""
        plaintext = "João da Silva Júnior"
        encrypted = encrypt_field(plaintext)
        decrypted = decrypt_field(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_encrypted_output_differs_from_plaintext(self):
        """Ciphertext must not equal the plaintext."""
        plaintext = "12345678909"
        encrypted = encrypt_field(plaintext)
        self.assertNotEqual(encrypted, plaintext)

    def test_different_ciphertexts_for_same_plaintext(self):
        """Each encryption should produce a different ciphertext (random nonce)."""
        plaintext = "12345678909"
        encrypted1 = encrypt_field(plaintext)
        encrypted2 = encrypt_field(plaintext)
        self.assertNotEqual(encrypted1, encrypted2)

    def test_both_decrypt_to_same_plaintext(self):
        """Different ciphertexts of the same plaintext should decrypt to the same value."""
        plaintext = "11987654321"
        encrypted1 = encrypt_field(plaintext)
        encrypted2 = encrypt_field(plaintext)
        self.assertEqual(decrypt_field(encrypted1), decrypt_field(encrypted2))
        self.assertEqual(decrypt_field(encrypted1), plaintext)

    def test_empty_string_encrypt(self):
        """Empty string should return empty string."""
        self.assertEqual(encrypt_field(''), '')
        self.assertEqual(decrypt_field(''), '')

    def test_none_handling(self):
        """None-like values should not crash."""
        self.assertEqual(encrypt_field(''), '')

    def test_ciphertext_is_base64(self):
        """Encrypted output should be valid base64."""
        encrypted = encrypt_field("test data")
        decoded = base64.b64decode(encrypted)
        # Should be at least 12 (nonce) + 16 (tag) + some data
        self.assertGreaterEqual(len(decoded), 29)


class TestHMACBlindIndex(unittest.TestCase):
    """Tests for HMAC-SHA256 blind index computation."""

    def test_deterministic(self):
        """Same input should always produce the same hash."""
        value = "12345678909"
        hash1 = compute_blind_index(value)
        hash2 = compute_blind_index(value)
        self.assertEqual(hash1, hash2)

    def test_different_inputs_different_hashes(self):
        """Different inputs should produce different hashes."""
        hash1 = compute_blind_index("12345678909")
        hash2 = compute_blind_index("98765432100")
        self.assertNotEqual(hash1, hash2)

    def test_normalized_input(self):
        """Input with formatting should produce the same hash as digits-only."""
        hash1 = compute_blind_index("123.456.789-09")
        hash2 = compute_blind_index("12345678909")
        self.assertEqual(hash1, hash2)

    def test_phone_normalization(self):
        """Phone with formatting should match digits-only."""
        hash1 = compute_blind_index("(11) 98765-4321")
        hash2 = compute_blind_index("11987654321")
        self.assertEqual(hash1, hash2)

    def test_empty_string(self):
        """Empty string should return empty string."""
        self.assertEqual(compute_blind_index(''), '')

    def test_hex_digest_format(self):
        """Output should be a 64-character hex string (SHA-256)."""
        result = compute_blind_index("12345678909")
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in result))


class TestCPFValidation(unittest.TestCase):
    """Tests for Brazilian CPF validation."""

    def test_valid_cpf(self):
        """Known valid CPFs should pass validation."""
        valid_cpfs = [
            "529.982.247-25",
            "52998224725",
            "111.444.777-35",
            "11144477735",
        ]
        for cpf in valid_cpfs:
            with self.subTest(cpf=cpf):
                self.assertTrue(validate_cpf(cpf), f"CPF {cpf} should be valid")

    def test_invalid_cpf_wrong_digits(self):
        """CPFs with wrong check digits should fail."""
        self.assertFalse(validate_cpf("529.982.247-26"))  # last digit wrong
        self.assertFalse(validate_cpf("12345678901"))

    def test_invalid_cpf_all_same_digits(self):
        """CPFs with all same digits should be rejected."""
        for d in range(10):
            cpf = str(d) * 11
            self.assertFalse(validate_cpf(cpf), f"CPF {cpf} (all same) should be invalid")

    def test_invalid_cpf_wrong_length(self):
        """CPFs with wrong length should fail."""
        self.assertFalse(validate_cpf("1234"))
        self.assertFalse(validate_cpf("123456789012"))
        self.assertFalse(validate_cpf(""))


class TestMasking(unittest.TestCase):
    """Tests for CPF and phone masking."""

    def test_mask_cpf_formatted(self):
        """Masked CPF should show only last 2 digits."""
        result = mask_cpf("529.982.247-25")
        self.assertEqual(result, "***.***.***.25")

    def test_mask_cpf_unformatted(self):
        """Unformatted CPF should also be masked correctly."""
        result = mask_cpf("52998224725")
        self.assertEqual(result, "***.***.***.25")

    def test_mask_cpf_invalid_length(self):
        """Invalid CPF should return fully masked."""
        result = mask_cpf("1234")
        self.assertEqual(result, "***.***.***-**")

    def test_mask_phone(self):
        """Masked phone should show only last 4 digits."""
        result = mask_phone("(11) 98765-4321")
        self.assertEqual(result, "(**) *****-4321")

    def test_mask_phone_short(self):
        """Short phone should return fully masked."""
        result = mask_phone("123")
        self.assertEqual(result, "(**) *****-****")


class TestNormalization(unittest.TestCase):
    """Tests for CPF and phone normalization."""

    def test_normalize_cpf(self):
        self.assertEqual(normalize_cpf("529.982.247-25"), "52998224725")

    def test_normalize_phone(self):
        self.assertEqual(normalize_phone("(11) 98765-4321"), "11987654321")

    def test_normalize_already_clean(self):
        self.assertEqual(normalize_cpf("52998224725"), "52998224725")


class TestKeyGeneration(unittest.TestCase):
    """Tests for key generation utilities."""

    def test_generate_encryption_key_length(self):
        """Generated key should decode to 32 bytes."""
        key_b64 = generate_encryption_key()
        key = base64.b64decode(key_b64)
        self.assertEqual(len(key), 32)

    def test_generate_hmac_key_length(self):
        """Generated HMAC key should decode to 32 bytes."""
        key_b64 = generate_hmac_key()
        key = base64.b64decode(key_b64)
        self.assertEqual(len(key), 32)

    def test_generated_keys_are_unique(self):
        """Each call should produce a different key."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        self.assertNotEqual(key1, key2)

    def test_generated_key_is_valid_base64(self):
        """Generated key should be valid base64."""
        key_b64 = generate_encryption_key()
        decoded = base64.b64decode(key_b64)
        re_encoded = base64.b64encode(decoded).decode()
        self.assertEqual(key_b64, re_encoded)


if __name__ == '__main__':
    unittest.main()
