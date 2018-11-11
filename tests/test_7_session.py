import os
import time

import pytest
from cryptojwt.jws.jws import JWS
from cryptojwt.key_bundle import KeyBundle
from cryptojwt.key_jar import init_key_jar
from cryptojwt.key_jar import KeyJar
from jwkest.jws import alg2keytype

from oidcmsg.exception import MessageException
from oidcmsg.exception import NotForMe
from oidcmsg.oidc import verified_claim_name
from oidcmsg.oidc import Claims
from oidcmsg.oidc import ClaimsRequest
from oidcmsg.oidc import IdToken
from oidcmsg.oidc.session import BACK_CHANNEL_LOGOUT_EVENT, \
    BackChannelLogoutRequest
from oidcmsg.oidc.session import LogoutToken
from oidcmsg.oidc.session import CheckSessionRequest
from oidcmsg.oidc.session import EndSessionRequest
from oidcmsg.oidc.session import EndSessionResponse
from oidcmsg.time_util import utc_time_sans_frac

CLIENT_ID = "client_1"
ISS = 'https://example.com'

IDTOKEN = IdToken(iss=ISS, sub="sub",
                  aud=CLIENT_ID, exp=utc_time_sans_frac() + 300,
                  nonce="N0nce", iat=time.time())
KC_SYM_S = KeyBundle(
    {
        "kty": "oct", "key": "abcdefghijklmnop".encode("utf-8"), "use": "sig",
        "alg": "HS256"
        })

NOW = utc_time_sans_frac()

KEYDEF = [
    {"type": "EC", "crv": "P-256", "use": ["sig"]},
    {"type": "EC", "crv": "P-256", "use": ["enc"]}
    ]

_dirname = os.path.dirname(os.path.abspath(__file__))

CLI_KEY = init_key_jar(public_path='{}/pub_client.jwks'.format(_dirname),
                       private_path='{}/priv_client.jwks'.format(_dirname),
                       key_defs=KEYDEF, owner=CLIENT_ID)

ISS_KEY = init_key_jar(public_path='{}/pub_iss.jwks'.format(_dirname),
                       private_path='{}/priv_iss.jwks'.format(_dirname),
                       key_defs=KEYDEF, owner=ISS)

ISS_KEY.import_jwks_as_json(open('{}/pub_client.jwks'.format(_dirname)).read(),
                            CLIENT_ID)

CLI_KEY.import_jwks_as_json(open('{}/pub_iss.jwks'.format(_dirname)).read(),
                            ISS)


class TestEndSessionResponse(object):
    def test_example(self):
        esr = EndSessionResponse()
        pass


class TestEndSessionRequest(object):
    def test_example(self):
        _symkey = KC_SYM_S.get(alg2keytype("HS256"))
        esreq = EndSessionRequest(
            id_token_hint=IDTOKEN.to_jwt(key=_symkey, algorithm="HS256",
                                         lifetime=300),
            redirect_url="http://example.org/jqauthz",
            state="state0")

        request = EndSessionRequest().from_urlencoded(esreq.to_urlencoded())
        keyjar = KeyJar()
        for _key in _symkey:
            keyjar.add_symmetric('', _key.key)
            keyjar.add_symmetric(ISS, _key.key)
            keyjar.add_symmetric(CLIENT_ID, _key.key)
        request.verify(keyjar=keyjar)
        assert isinstance(request, EndSessionRequest)
        assert set(request.keys()) == {verified_claim_name('id_token_hint'),
                                       'id_token_hint', 'redirect_url', 'state'}
        assert request["state"] == "state0"
        assert request[
                   verified_claim_name("id_token_hint")]["aud"] == ["client_1"]


class TestCheckSessionRequest(object):
    def test_example(self):
        _symkey = KC_SYM_S.get(alg2keytype("HS256"))
        csr = CheckSessionRequest(
            id_token=IDTOKEN.to_jwt(key=_symkey, algorithm="HS256",
                                    lifetime=300))
        keyjar = KeyJar()
        keyjar.add_kb('', KC_SYM_S)
        assert csr.verify(keyjar=keyjar)


class TestClaimsRequest(object):
    def test_example(self):
        claims = {
            "name": {"essential": True},
            "nickname": None,
            "email": {"essential": True},
            "verified": {"essential": True},
            "picture": None
            }

        cr = ClaimsRequest(userinfo=Claims(**claims),
                           id_token=Claims(auth_time=None,
                                           acr={"values": ["2"]}))
        cr.verify()
        _url = cr.to_urlencoded()
        cr1 = ClaimsRequest().from_urlencoded(_url)
        cr1.verify()

        _js = cr.to_json()
        cr1 = ClaimsRequest().from_json(_js)
        cr1.verify()


def test_logout_token_1():
    val = {
        "iss": ISS,
        "sub": "248289761001",
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    assert lt.verify()


def test_logout_token_2():
    val = {
        "iss": ISS,
        "sub": "248289761001",
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    assert lt.verify()


def test_logout_token_3():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    assert lt.verify()


def test_logout_token_4():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(ValueError):
        lt.verify()


def test_logout_token_5():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {'foo':'bar'}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(ValueError):
        lt.verify()


def test_logout_token_6():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "events": {
            "http://schemas.openid.net/event/foo": {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(ValueError):
        lt.verify()


def test_logout_token_7():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {},
            "http://schemas.openid.net/event/foo": {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(ValueError):
        lt.verify()


def test_logout_token_with_nonce():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            },
        "nonce": "1234567890"
        }
    lt = LogoutToken(**val)
    with pytest.raises(MessageException):
        lt.verify()


def test_logout_token_wrong_iat():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW+10,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(ValueError):
        lt.verify()

    # Within allowed clock skew
    lt.verify(skew=60)


def test_logout_token_wrong_aud():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(NotForMe):
        lt.verify(aud='deep_purple')

    lt.verify(aud=CLIENT_ID)


def test_logout_token_wrong_iss():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    with pytest.raises(NotForMe):
        lt.verify(iss='deep_purple')

    lt.verify(iss=ISS)


def test_back_channel_logout_request():
    val = {
        "iss": ISS,
        "aud": [CLIENT_ID],
        "iat": NOW,
        "jti": "bWJq",
        "sid": "08a5019c-17e1-4977-8f42-65a12843ea02",
        "events": {
            BACK_CHANNEL_LOGOUT_EVENT: {}
            }
        }
    lt = LogoutToken(**val)
    signer = JWS(lt.to_json(), alg='ES256')
    _jws = signer.sign_compact(keys=ISS_KEY.get_signing_key(owner=ISS))

    bclr = BackChannelLogoutRequest(logout_token=_jws)

    # This is how it is posted
    _req = bclr.to_urlencoded()

    _request = BackChannelLogoutRequest().from_urlencoded(_req)

    assert 'logout_token' in _request

    _verified = _request.verify(keyjar=CLI_KEY, iss=ISS,
                                                     aud=CLIENT_ID, skew=30)

    assert _verified
    assert set(_request.keys()) == {'logout_token', '__verified_logout_token'}
