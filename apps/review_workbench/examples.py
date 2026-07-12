from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoExample:
    id: str
    title: str
    description: str
    mode: str
    language: str
    framework: str
    risk_level: str
    context: str
    diff_text: str


PAYMENT_SECURITY_DIFF = """diff --git a/payment.py b/payment.py
index 1111111..2222222 100644
--- a/payment.py
+++ b/payment.py
@@ -1,9 +1,17 @@
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


RETRY_RELIABILITY_DIFF = """diff --git a/catalog.py b/catalog.py
index 3333333..4444444 100644
--- a/catalog.py
+++ b/catalog.py
@@ -1,5 +1,13 @@
 import requests
 
-def fetch_catalog(url):
-    return requests.get(url, timeout=3).json()
+def fetch_catalog(url, attempts=3):
+    for attempt in range(attempts):
+        try:
+            response = requests.get(url, timeout=3)
+            response.raise_for_status()
+            return response.json()
+        except Exception:
+            continue
+    return None
"""


EXAMPLES = (
    DemoExample(
        id="payment-security",
        title="Payment security regression",
        description="Find credential leakage and unsafe recursive retries.",
        mode="review",
        language="python",
        framework="pytest",
        risk_level="critical",
        context="Payment service handling authenticated charges.",
        diff_text=PAYMENT_SECURITY_DIFF,
    ),
    DemoExample(
        id="retry-reliability",
        title="Retry reliability gap",
        description="Design tests for broad exception handling and retry exhaustion.",
        mode="tests",
        language="python",
        framework="pytest",
        risk_level="high",
        context="Catalog client used in a latency-sensitive request path.",
        diff_text=RETRY_RELIABILITY_DIFF,
    ),
)
