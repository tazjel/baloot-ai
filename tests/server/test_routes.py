import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mock settings to use in-memory DB
import server.settings
server.settings.DB_URI = 'sqlite://:memory:'
server.settings.DB_POOL_SIZE = 1
server.settings.DB_MIGRATE = True

from server.common import db
# Import models to define tables
import server.models

from server.routes import auth, shop
from py4web import HTTP
from ombott import HTTPError
import server.auth_utils as auth_utils

@pytest.fixture(autouse=True)
def clean_db():
    # Clean up app_user before each test
    db.app_user.truncate()
    db.commit()
    yield
    db.app_user.truncate()
    db.commit()

@pytest.fixture
def mock_ctx():
    req = MagicMock()
    req.headers = {}
    req.json = {}
    req.user = {}

    res = MagicMock()
    res.status = 200

    # Patch in auth
    p1 = patch('server.routes.auth.request', req)
    p2 = patch('server.routes.auth.response', res)
    # Patch in shop
    p3 = patch('server.routes.shop.request', req)
    p4 = patch('server.routes.shop.response', res)

    p1.start(); p2.start(); p3.start(); p4.start()

    yield req, res

    p1.stop(); p2.stop(); p3.stop(); p4.stop()

@pytest.fixture
def mock_auth():
    with patch('server.auth_utils.verify_token') as mock_verify:
        yield mock_verify

def test_signup(mock_ctx):
    req, res_obj = mock_ctx
    req.json = {
        "firstName": "Test",
        "lastName": "User",
        "email": "signup@test.com",
        "password": "password123"
    }

    # signup returns a dict
    res = auth.signup()

    assert res['email'] == "signup@test.com"
    assert 'user_id' in res

    # Verify DB defaults
    user = db(db.app_user.email == "signup@test.com").select().first()
    assert user is not None
    assert user.coins == 1000
    assert user.owned_items == ['card_default', 'table_default']
    assert user.equipped_items['card'] == 'card_default'

def test_signin_returns_profile(mock_ctx):
    req, res_obj = mock_ctx
    # Create user
    import bcrypt
    hashed = bcrypt.hashpw(b"password123", bcrypt.gensalt())

    uid = db.app_user.insert(
        first_name="Login", last_name="User",
        email="login@test.com", password=hashed
    )
    db.commit()

    req.json = {
        "email": "login@test.com",
        "password": "password123"
    }

    res = auth.signin()

    assert res['email'] == "login@test.com"
    assert 'token' in res
    assert res['coins'] == 1000
    assert 'ownedItems' in res

def test_shop_purchase(mock_ctx, mock_auth):
    req, res_obj = mock_ctx
    # Setup user
    uid = db.app_user.insert(
        first_name="Shop", last_name="Buyer",
        email="buyer@test.com", password="hash",
        coins=1000, owned_items=['default']
    )
    db.commit()

    # Mock auth token
    req.headers = {'Authorization': 'Bearer fake-token'}
    mock_auth.return_value = {'user_id': uid}

    req.json = {'itemId': 'shiny_card', 'cost': 500}

    res = shop.purchase_item()

    assert res['success'] == True
    assert res['coins'] == 500
    assert 'shiny_card' in res['ownedItems']

    # Verify DB
    u = db.app_user(uid)
    assert u.coins == 500
    assert 'shiny_card' in u.owned_items

def test_shop_purchase_insufficient_funds(mock_ctx, mock_auth):
    req, res_obj = mock_ctx
    uid = db.app_user.insert(
        first_name="Poor", last_name="Guy",
        email="poor@test.com", password="hash",
        coins=100
    )
    db.commit()

    req.headers = {'Authorization': 'Bearer fake-token'}
    mock_auth.return_value = {'user_id': uid}

    req.json = {'itemId': 'expensive', 'cost': 500}

    # py4web abort raises HTTPError
    with pytest.raises(HTTPError) as excinfo:
        shop.purchase_item()

    assert excinfo.value.status_code == 400
    assert "Insufficient funds" in str(excinfo.value)

def test_shop_equip(mock_ctx, mock_auth):
    req, res_obj = mock_ctx
    uid = db.app_user.insert(
        first_name="Equip", last_name="User",
        email="equip@test.com", password="hash",
        coins=1000,
        owned_items=['default', 'special_table'],
        equipped_items={'table': 'default'}
    )
    db.commit()

    req.headers = {'Authorization': 'Bearer fake-token'}
    mock_auth.return_value = {'user_id': uid}

    req.json = {'itemId': 'special_table', 'type': 'table'}

    res = shop.equip_item()

    assert res['success'] == True
    assert res['equippedItems']['table'] == 'special_table'

    # Verify DB
    u = db.app_user(uid)
    assert u.equipped_items['table'] == 'special_table'

def test_shop_equip_not_owned(mock_ctx, mock_auth):
    req, res_obj = mock_ctx
    uid = db.app_user.insert(
        first_name="Cheater", last_name="User",
        email="cheat@test.com", password="hash",
        owned_items=['default']
    )
    db.commit()

    req.headers = {'Authorization': 'Bearer fake-token'}
    mock_auth.return_value = {'user_id': uid}

    req.json = {'itemId': 'god_mode_card', 'type': 'card'}

    with pytest.raises(HTTPError) as excinfo:
        shop.equip_item()

    assert excinfo.value.status_code == 400
