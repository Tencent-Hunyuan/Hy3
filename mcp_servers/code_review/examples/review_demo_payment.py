"""Small code-review demo target for the Hy3 MCP server."""

from __future__ import annotations

import requests


PAYMENT_ENDPOINT = "https://payments.example.com/charge"


def charge_user(user_id: str, amount: float, token: str) -> dict:
    print("charging", user_id, amount, token)

    response = requests.post(
        PAYMENT_ENDPOINT,
        json={
            "user_id": user_id,
            "amount": amount,
            "token": token,
        },
        timeout=1,
    )

    if response.status_code >= 500:
        return charge_user(user_id, amount, token)

    response.raise_for_status()
    return response.json()


def build_demo_patch() -> str:
    return """diff --git a/payment.py b/payment.py
index 1111111..2222222 100644
--- a/payment.py
+++ b/payment.py
@@ -1,8 +1,20 @@
 import requests
 
 def charge_user(user_id, amount, token):
+    print("charging", user_id, amount, token)
     response = requests.post(
         "https://payments.example.com/charge",
         json={"user_id": user_id, "amount": amount, "token": token},
+        timeout=1,
     )
+    if response.status_code >= 500:
+        return charge_user(user_id, amount, token)
     response.raise_for_status()
     return response.json()
"""
