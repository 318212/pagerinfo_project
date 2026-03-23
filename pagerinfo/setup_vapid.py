"""
pagerinfo/setup_vapid.py
Run ONCE to generate VAPID keys for push notifications.
Keys are saved to data/vapid_keys.json — keep them private.

Usage: python setup_vapid.py
"""

import json
from pathlib import Path

def generate_vapid_keys():
    try:
        from py_vapid import Vapid
    except ImportError:
        print("❌ py_vapid not installed. Run: pip install py-vapid")
        return

    out = Path("data/vapid_keys.json")
    if out.exists():
        print("⚠️  VAPID keys already exist at data/vapid_keys.json")
        print("   Delete that file first if you want to regenerate.")
        return

    v = Vapid()
    v.generate_keys()

    keys = {
        "private_key": v.private_key.private_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization",
                                fromlist=["Encoding"]).Encoding.PEM,
            format=__import__("cryptography.hazmat.primitives.serialization",
                              fromlist=["PrivateFormat"]).PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=__import__("cryptography.hazmat.primitives.serialization",
                                            fromlist=["NoEncryption"]).NoEncryption(),
        ).decode(),
        "public_key": v.public_key.public_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization",
                                fromlist=["Encoding"]).Encoding.X962,
            format=__import__("cryptography.hazmat.primitives.serialization",
                              fromlist=["PublicFormat"]).PublicFormat.UncompressedPoint,
        ).hex(),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(keys, indent=2))

    print("✅ VAPID keys generated and saved to data/vapid_keys.json")
    print(f"\n   Public key (paste into static/js/app.js):")
    print(f"   {keys['public_key']}\n")
    print("⚠️  Keep data/vapid_keys.json private — never commit it to git!")

if __name__ == "__main__":
    generate_vapid_keys()
