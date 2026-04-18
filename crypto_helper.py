"""
crypto_helper.py — Szyfrowanie/deszyfrowanie plików z danymi osobowymi.

Naprawka F-02 (RODO art. 25, 32(1)(a)):
  Dane osobowe zapisywane są w plikach szyfrowanych AES-256-GCM (Fernet)
  z kluczem pochodnym od hasła użytkownika (PBKDF2-SHA256, 480 000 iteracji).

Format pliku binarnego:
  [16 B sól PBKDF2] + [zaszyfrowane bajty Fernet (zawierają nonce i tag GCM)]

Wymagana biblioteka: pip install cryptography
"""

import base64
import json
import os

_PBKDF2_ITERATIONS = 480_000   # OWASP 2023: min 210 000 dla SHA-256
_SALT_SIZE         = 16        # 128-bitowa sól


def _derive_key(password: str, salt: bytes) -> bytes:
    """Wyprowadza 256-bitowy klucz z hasła i soli metodą PBKDF2-SHA256."""
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def zapisz_zaszyfrowany(sciezka: str, dane, haslo: str) -> None:
    """
    Serializuje dane (lista lub słownik) do JSON, szyfruje i zapisuje do pliku.

    Rzuca:
        ImportError — gdy biblioteka cryptography nie jest zainstalowana
        OSError     — przy błędzie zapisu
    """
    from cryptography.fernet import Fernet
    salt         = os.urandom(_SALT_SIZE)
    klucz        = _derive_key(haslo, salt)
    json_bytes   = json.dumps(dane, ensure_ascii=False, indent=2).encode("utf-8")
    zaszyfrowane = Fernet(klucz).encrypt(json_bytes)
    with open(sciezka, "wb") as fp:
        fp.write(salt + zaszyfrowane)


def wczytaj_zaszyfrowany(sciezka: str, haslo: str):
    """
    Odczytuje plik, odszyfrowuje i zwraca dane (lista lub słownik).

    Rzuca:
        ImportError — gdy biblioteka cryptography nie jest zainstalowana
        ValueError  — przy złym haśle lub uszkodzonym pliku
        OSError     — przy błędzie odczytu
    """
    from cryptography.fernet import Fernet, InvalidToken
    with open(sciezka, "rb") as fp:
        raw = fp.read()
    if len(raw) <= _SALT_SIZE:
        raise ValueError("Plik jest uszkodzony lub nie jest zaszyfrowaną bazą danych.")
    salt, zaszyfrowane = raw[:_SALT_SIZE], raw[_SALT_SIZE:]
    klucz = _derive_key(haslo, salt)
    try:
        json_bytes = Fernet(klucz).decrypt(zaszyfrowane)
    except InvalidToken:
        raise ValueError(
            "Nieprawidłowe hasło lub uszkodzony plik.\n"
            "Sprawdź hasło i spróbuj ponownie."
        )
    return json.loads(json_bytes.decode("utf-8"))


def czy_cryptography_dostepne() -> bool:
    """Zwraca True jeśli biblioteka cryptography jest zainstalowana."""
    try:
        import cryptography  # noqa: F401
        return True
    except ImportError:
        return False
