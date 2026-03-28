#!/usr/bin/env python3
"""
Helper script to generate a valid Fernet encryption key.

Usage:
    python scripts/generate_encryption_key.py

Copy the printed key into your .env file as ENCRYPTION_KEY.
Keep this key secret and never commit it to version control.
"""

from cryptography.fernet import Fernet


def main() -> None:
    """Generate and print a new Fernet encryption key."""
    key = Fernet.generate_key()
    print("=" * 60)
    print("Generated Fernet Encryption Key")
    print("=" * 60)
    print(f"\nENCRYPTION_KEY={key.decode()}\n")
    print("⚠  Store this key securely. Losing it means all")
    print("   encrypted data becomes permanently unreadable.")
    print("=" * 60)


if __name__ == "__main__":
    main()
