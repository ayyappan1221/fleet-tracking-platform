"""Password strength policy + email OTP verification + OTP login."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User
from tests.conftest import test_engine, TestingSessionLocal


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def _register(client, email, password='Secret123!', role='driver', name='OTP User'):
    return client.post(
        '/api/auth/register',
        json={'email': email, 'name': name, 'password': password, 'role': role},
    )


def _dev_otp(reg):
    assert reg.status_code == 201, reg.text
    return reg.json()['data']['dev_otp']


def _verify(client, email, code, purpose='signup_verify'):
    return client.post(
        '/api/auth/verify-signup' if purpose == 'signup_verify' else '/api/auth/login/otp',
        json={'email': email, 'code': code, 'purpose': purpose},
    )


# ----- password strength ------------------------------------------------------

@pytest.mark.parametrize(
    'password',
    [
        'Short1!',      # too short
        'alllowercase1!',  # no uppercase
        'ALLUPPERCASE1!',  # no lowercase
        'NoDigitsHere!',   # no digit
        'NoSpecial123',    # no special char
    ],
)
def test_weak_passwords_rejected(client, password):
    resp = _register(client, 'weakrule@test.com', password=password)
    assert resp.status_code == 422, resp.text


def test_strong_password_accepted(client):
    resp = _register(client, 'strong@test.com', password='Secret123!')
    assert resp.status_code == 201, resp.text


# ----- signup verification ----------------------------------------------------

def test_register_returns_dev_otp_outside_production(client):
    reg = _register(client, 'otp1@test.com')
    assert reg.status_code == 201
    assert 'dev_otp' in reg.json()['data']
    assert len(reg.json()['data']['dev_otp']) == 6


def test_login_blocked_until_verified(client):
    _register(client, 'unverified@test.com')
    login = client.post(
        '/api/auth/login',
        data={'username': 'unverified@test.com', 'password': 'Secret123!'},
    )
    assert login.status_code == 403
    assert 'not verified' in login.json()['detail'].lower()


def test_verify_signup_then_password_login(client):
    reg = _register(client, 'verifyme@test.com')
    verify = _verify(client, 'verifyme@test.com', _dev_otp(reg))
    assert verify.status_code == 200, verify.text
    login = client.post(
        '/api/auth/login',
        data={'username': 'verifyme@test.com', 'password': 'Secret123!'},
    )
    assert login.status_code == 200, login.text
    assert login.json()['data']['access_token']


def test_verify_signup_wrong_code_rejected(client):
    reg = _register(client, 'wrongcode@test.com')
    assert reg.status_code == 201
    resp = _verify(client, 'wrongcode@test.com', '000000')
    assert resp.status_code == 400


def test_verify_signup_code_single_use(client):
    reg = _register(client, 'singleuse@test.com')
    code = _dev_otp(reg)
    first = _verify(client, 'singleuse@test.com', code)
    assert first.status_code == 200
    second = _verify(client, 'singleuse@test.com', code)
    assert second.status_code == 404


def test_otp_attempts_lock_out(client):
    reg = _register(client, 'locked@test.com')
    assert reg.status_code == 201
    for _ in range(5):
        resp = _verify(client, 'locked@test.com', '000000')
        assert resp.status_code == 400
    resp = _verify(client, 'locked@test.com', '000000')
    assert resp.status_code == 429


def test_request_otp_cooldown(client):
    _register(client, 'cool@test.com')
    resp = client.post(
        '/api/auth/request-otp',
        json={'email': 'cool@test.com', 'purpose': 'signup_verify'},
    )
    assert resp.status_code == 429


# ----- OTP login --------------------------------------------------------------

def test_otp_login_full_flow(client):
    reg = _register(client, 'otplogin@test.com')
    assert _verify(client, 'otplogin@test.com', _dev_otp(reg)).status_code == 200

    req = client.post(
        '/api/auth/request-otp',
        json={'email': 'otplogin@test.com', 'purpose': 'login_otp'},
    )
    assert req.status_code == 200, req.text
    code = req.json()['data']['dev_otp']

    login = client.post(
        '/api/auth/login/otp',
        json={'email': 'otplogin@test.com', 'code': code, 'purpose': 'login_otp'},
    )
    assert login.status_code == 200, login.text
    assert login.json()['data']['access_token']


def test_otp_login_unknown_email_404(client):
    resp = client.post(
        '/api/auth/request-otp',
        json={'email': 'nobody@test.com', 'purpose': 'login_otp'},
    )
    assert resp.status_code == 404


def test_otp_login_wrong_code_rejected(client):
    reg = _register(client, 'otpbad@test.com')
    assert _verify(client, 'otpbad@test.com', _dev_otp(reg)).status_code == 200
    req = client.post(
        '/api/auth/request-otp',
        json={'email': 'otpbad@test.com', 'purpose': 'login_otp'},
    )
    assert req.status_code == 200
    login = client.post(
        '/api/auth/login/otp',
        json={'email': 'otpbad@test.com', 'code': '000000', 'purpose': 'login_otp'},
    )
    assert login.status_code == 400


def test_otp_login_token_accesses_protected_route(client):
    reg = _register(client, 'otpaccess@test.com')
    assert _verify(client, 'otpaccess@test.com', _dev_otp(reg)).status_code == 200
    req = client.post(
        '/api/auth/request-otp',
        json={'email': 'otpaccess@test.com', 'purpose': 'login_otp'},
    )
    code = req.json()['data']['dev_otp']
    login = client.post(
        '/api/auth/login/otp',
        json={'email': 'otpaccess@test.com', 'code': code, 'purpose': 'login_otp'},
    )
    token = login.json()['data']['access_token']
    resp = client.get(
        '/api/vehicles/', headers={'Authorization': f'Bearer {token}'}
    )
    assert resp.status_code == 200


# ----- strength unit checks ---------------------------------------------------

def test_strength_checker_lists_every_missing_rule():
    from app.core.password import check_password_strength

    assert check_password_strength('Secret123!') == []
    unmet = check_password_strength('abc')
    assert len(unmet) == 4  # length, upper, digit, special
