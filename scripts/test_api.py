import os

import requests

# The base URL of your local FastAPI server
BASE_URL = "http://localhost:8000"

# Read credentials from environment (set in .env)
_USERNAME = "admin"
_PASSWORD = os.environ.get("DEMO_PASSWORD", "")
if not _PASSWORD:
    raise RuntimeError("DEMO_PASSWORD env var is not set. Add it to your .env file.")


def test_workflow():
    print("1. Logging in to get token...")
    auth_response = requests.post(
        f"{BASE_URL}/token", data={"username": _USERNAME, "password": _PASSWORD}
    )

    if auth_response.status_code != 200:
        print("Login failed!", auth_response.json())
        return

    token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful! Token acquired.\n")

    print("2. Testing Batch Prediction...")
    batch_payload = {
        "texts": [
            "Hey team, just following up on the meeting notes.",
            "URGENT: Your account will be suspended. Verify here: http://fake-bank.com/login",
        ]
    }
    batch_response = requests.post(
        f"{BASE_URL}/api/v1/predict/batch", json=batch_payload, headers=headers
    )
    print("Batch Prediction Results:\n", batch_response.json())


if __name__ == "__main__":
    test_workflow()
