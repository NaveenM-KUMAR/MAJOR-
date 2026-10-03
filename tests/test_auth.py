from app.models.user import User
from app.services.auth_service import register_user, authenticate_user

def test_driver_registration(app):
    with app.test_request_context():
        success, user = register_user(
            name="New Driver",
            email="newdriver@test.com",
            phone="9988776655",
            password="secretpassword",
            role="DRIVER"
        )
        assert success is True
        assert user.role == "DRIVER"
        assert user.status == "ACTIVE"
        assert user.check_password("secretpassword") is True

def test_owner_registration_pending_status(app):
    with app.test_request_context():
        success, owner = register_user(
            name="New Owner",
            email="newowner@test.com",
            phone="9988776654",
            password="secretpassword",
            role="OWNER",
            owner_address="100 Feet Rd"
        )
        assert success is True
        assert owner.role == "OWNER"
        assert owner.owner_status == "PENDING"
        assert owner.is_approved_owner is False

def test_duplicate_registration_fails(app, test_data):
    with app.test_request_context():
        success, err = register_user(
            name="Duplicate",
            email="driver@test.com",
            phone="1234567890",
            password="password"
        )
        assert success is False
        assert "already exists" in err

def test_authentication_success_and_failure(app, test_data):
    with app.test_request_context():
        # Correct login
        success, user = authenticate_user("driver@test.com", "pass123")
        assert success is True
        assert user.email == "driver@test.com"

        # Wrong password
        success, err = authenticate_user("driver@test.com", "wrongpass")
        assert success is False
        assert "Invalid email address or password" in err

def test_driver_login_redirects_to_dashboard(client, test_data):
    # Post login form as driver
    res = client.post('/login', data={
        'email': 'driver@test.com',
        'password': 'pass123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Driver Command Center" in res.data or b"Driver Dashboard" in res.data or b"Popular Parking Areas" in res.data

