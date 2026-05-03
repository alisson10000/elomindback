from utils.security import decrypt_value, encrypt_value, hash_email


def test_encrypt_value_hides_plaintext_and_decrypts_back():
    raw_value = "sensitive.person@example.com"

    encrypted = encrypt_value(raw_value)
    decrypted = decrypt_value(encrypted)

    assert encrypted != raw_value
    assert decrypted == raw_value
    assert raw_value not in encrypted
    assert "sensitive.person" not in encrypted


def test_hash_email_is_deterministic_and_non_reversible():
    email = "same@example.com"
    same_hash = hash_email(email)
    same_hash_again = hash_email("same@example.com")
    other_hash = hash_email("other@example.com")

    assert same_hash == same_hash_again
    assert same_hash != other_hash
    assert email not in same_hash
    assert "@example.com" not in same_hash
