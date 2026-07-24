import requests

# Test Health
try:
    r = requests.get("http://localhost:8000/api/v1/health/")
    print(f"Health: {r.status_code}")
except Exception as e:
    print(f"Health Error: {e}")

# Test Register
try:
    r = requests.post(
        "http://localhost:8000/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "is_superuser": False
        }
    )
    print(f"Register: {r.status_code} - {r.text}")
except Exception as e:
    print(f"Register Error: {e}")

# Test Login
try:
    r = requests.post(
        "http://localhost:8000/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "password123"
        }
    )
    print(f"Login: {r.status_code} - {r.text}")
except Exception as e:
    print(f"Login Error: {e}")
