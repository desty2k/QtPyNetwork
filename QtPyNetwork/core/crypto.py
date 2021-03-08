from cryptography.fernet import Fernet, InvalidToken


def encrypt(message: bytes, key: bytes) -> bytes:
    return Fernet(key).encrypt(message)


def decrypt(data: bytes, key: bytes) -> bytes:
    return Fernet(key).decrypt(data)


def generate_key():
    return Fernet.generate_key()


def validate_key(key: bytes):
    try:
        Fernet._get_unverified_token_data(key)  # noqa
        return True
    except InvalidToken:
        return False
