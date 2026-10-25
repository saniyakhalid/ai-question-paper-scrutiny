import os
import sys
import secrets
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_faculty_login():
    response = client.post("/api/auth/login", json={
        "email": "faculty@college.edu",
        "password": os.environ["TEST_USER_PASSWORD"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "FACULTY"


def test_moderator_login_returns_the_assigned_role():
    response = client.post("/api/auth/login", json={
        "email": "moderator@college.edu",
        "password": os.environ["TEST_USER_PASSWORD"]
    })
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "MODERATOR"


def test_administrator_can_create_a_moderator_login():
    login_response = client.post("/api/auth/login", json={
        "email": "admin@college.edu",
        "password": os.environ["TEST_USER_PASSWORD"]
    })
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    email = f"moderator-{secrets.token_hex(6)}@example.edu"

    create_response = client.post("/api/admin/users", headers={
        "Authorization": f"Bearer {token}"
    }, json={
        "email": email,
        "password": os.environ["TEST_USER_PASSWORD"],
        "full_name": "Created Moderator",
        "department": "Test Department",
        "role": "MODERATOR",
    })
    assert create_response.status_code == 201, create_response.text
    assert create_response.json()["role"] == "MODERATOR"

    moderator_login = client.post("/api/auth/login", json={
        "email": email,
        "password": os.environ["TEST_USER_PASSWORD"]
    })
    assert moderator_login.status_code == 200
    assert moderator_login.json()["user"]["role"] == "MODERATOR"

def test_invalid_login():
    response = client.post("/api/auth/login", json={
        "email": "faculty@college.edu",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_public_registration_cannot_assign_moderator_role():
    response = client.post("/api/auth/register", json={
        "email": f"new-{secrets.token_hex(6)}@example.edu",
        "password": os.environ["TEST_USER_PASSWORD"],
        "full_name": "New Test Faculty",
        "department": "Test Department",
        "role": "MODERATOR",
    })
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "FACULTY"
