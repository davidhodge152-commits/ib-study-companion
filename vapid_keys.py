"""
VAPID key generator for web push notifications.

Run this script to generate a new VAPID key pair:
    python vapid_keys.py

Add the output to your .env file.
"""

from __future__ import annotations


def generate_vapid_keys():
    """Generate a new VAPID key pair and print as env vars."""
    try:
        from py_vapid import Vapid
    except ImportError:
        print("Install pywebpush first: pip install pywebpush")
        return

    vapid = Vapid()
    vapid.generate_keys()

    print("Add these to your .env file:\n")
    print(f"VAPID_PRIVATE_KEY={vapid.private_pem()}")
    print(f"VAPID_PUBLIC_KEY={vapid.public_key_urlsafe_base64()}")
    print("VAPID_CLAIMS_EMAIL=mailto:admin@example.com")


if __name__ == "__main__":
    generate_vapid_keys()
