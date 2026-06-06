import logging
from base64 import urlsafe_b64encode as b64e

import pytest
from cryptography.fernet import InvalidToken

from bitcoin_safe_lib.storage import Encrypt, SaveAllClass, Storage, StorageDecryptError


class ExampleSaveable(SaveAllClass):
    VERSION = "1.0.0"

    def __init__(self, value: str, optional: str | None = None) -> None:
        self.value = value
        self.optional = optional


def test_from_dumps_prefers_dct_values_over_class_kwargs(caplog) -> None:
    json_string = (
        '{"__class__":"ExampleSaveable","VERSION":"1.0.0","value":"from_dct","optional":"from_json"}'
    )

    with caplog.at_level(logging.ERROR, logger="bitcoin_safe_lib.storage"):
        obj = ExampleSaveable._from_dumps(
            json_string,
            class_kwargs={"ExampleSaveable": {"value": "from_kwargs", "extra": "unused"}},
        )

    assert obj.value == "from_dct"
    assert obj.optional == "from_json"
    assert "Duplicate deserialization keys" in caplog.text
    assert "ExampleSaveable" in caplog.text
    assert "value" in caplog.text


def make_payload(iterations: int, encrypted_message: bytes = b"x") -> bytes:
    return b64e((b"s" * 16) + iterations.to_bytes(4, "big") + encrypted_message)


def test_password_encrypt_decrypt_round_trip() -> None:
    encrypt = Encrypt()

    token = encrypt.password_encrypt(b"secret", "pw")

    assert encrypt.password_decrypt(token, "pw") == b"secret"


@pytest.mark.parametrize("wrapper", [b"  %b  ", b"\t%b\t", b"\n%b\n", b" \t\n%b\n\t "])
def test_password_decrypt_strips_outer_whitespace(wrapper: bytes) -> None:
    encrypt = Encrypt()
    token = encrypt.password_encrypt(b"secret", "pw")

    wrapped_token = wrapper % token

    assert encrypt.password_decrypt(wrapped_token, "pw") == b"secret"


@pytest.mark.parametrize(
    ("token", "label"),
    [
        (b"", "empty"),
        (b'{"foo": 1', "truncated json"),
        (b"AAAA", "short base64"),
        (b"!!!", "invalid base64"),
        (make_payload(0), "zero iterations"),
        (make_payload(1_000_001), "too many iterations"),
    ],
)
def test_password_decrypt_rejects_malformed_payloads(token: bytes, label: str) -> None:
    encrypt = Encrypt()

    with pytest.raises(StorageDecryptError, match="Invalid encrypted payload"):
        encrypt.password_decrypt(token, "pw")


def test_password_decrypt_wrong_password_raises_invalid_token() -> None:
    encrypt = Encrypt()
    token = encrypt.password_encrypt(b"secret", "pw")

    with pytest.raises(InvalidToken):
        encrypt.password_decrypt(token, "wrong")


def test_has_password_detects_plaintext_and_encrypted_files(tmp_path) -> None:
    plaintext = tmp_path / "plain.wallet"
    truncated = tmp_path / "truncated.wallet"
    encrypted = tmp_path / "encrypted.wallet"
    encrypted_with_whitespace = tmp_path / "encrypted_with_whitespace.wallet"

    plaintext.write_text('{"foo": 1}')
    truncated.write_bytes(b'{"foo": 1')
    encrypted_token = Encrypt().password_encrypt(b"secret", "pw")
    encrypted.write_bytes(encrypted_token)
    encrypted_with_whitespace.write_bytes(b" \t\n" + encrypted_token + b"\n\t ")

    assert not Storage.has_password(str(plaintext))
    assert not Storage.has_password(str(truncated))
    assert Storage.has_password(str(encrypted))
    assert Storage.has_password(str(encrypted_with_whitespace))


def test_load_decrypts_encrypted_file_wrapped_in_whitespace(tmp_path) -> None:
    encrypted = tmp_path / "encrypted_with_whitespace.wallet"
    encrypted_token = Encrypt().password_encrypt(b"secret", "pw")
    encrypted.write_bytes(b" \t\n" + encrypted_token + b"\n\t ")

    assert Storage().load(str(encrypted), password="pw") == "secret"
