import os
import json
import jwt
import logging
from jose import jwt as jose_jwt
from jwt.utils import base64url_decode
from urllib.request import urlopen
from starlette.exceptions import HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED

jwt_authority_domain = os.environ["JWT_AUTHORITY_DOMAIN"]
jwt_audience = os.environ["JWT_AUDIENCE"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_public_key(kid: str) -> dict:
    try:
        json_url = urlopen(
            "https://" + jwt_authority_domain + "/protocol/openid-connect/certs"
        )
    except Exception as exception:
        return {}

    jwks = json.loads(json_url.read())
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == kid:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    if not rsa_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="no public key found for kid: {}".format(kid),
        )
    return rsa_key


def authenticate(credential: str) -> bool:
    _, token = credential.split(" ", 1)

    header, _, _ = token.rsplit(".", 2)

    jwt_header = json.loads(base64url_decode(header))
    kid = jwt_header["kid"]
    alg = jwt_header["alg"]
    try:
        public_key = get_public_key(kid)

        if public_key is None:
            return False

        decoded_jwt = jose_jwt.decode(
            token,
            algorithms=[alg],
            key=public_key,
            audience=jwt_audience,
        )
        if "sub" not in decoded_jwt or "tenant" not in decoded_jwt:
            return False

        return True

    except jwt.InvalidAudienceError as exc:
        logger.error("given audience is not valid, %s", exc)
        return False
    except jwt.InvalidAlgorithmError as exc:
        logger.error("jnvalid Jwt, %s", exc)
        return False
    except jwt.DecodeError as exc:
        logger.error("jwt decode error, %s", exc)
        return False
    except jwt.ExpiredSignatureError as exc:
        logger.error("jwt is expired, %s", exc)
        return False
    except Exception as exc:
        logger.error("invalid jwt, %s", exc)
        return False


def generate_policy(principal_id, effect, resource):
    policy = {"principalId": principal_id}

    if effect and resource:
        policy_document = {"Version": "2012-10-17", "Statement": []}
        statement_one = {
            "Action": "execute-api:Invoke",
            "Effect": effect,
            "Resource": resource,
        }
        policy_document["Statement"] = [statement_one]
        policy["policyDocument"] = policy_document
    policy["context"] = {"stringKey": "stringval", "numberKey": 123, "booleanKey": True}
    auth_response = json.dumps(policy)
    return auth_response


def lambda_handler(event, context):
    headers = event["headers"]
    credential = headers["Authorization"]

    is_authenticated = authenticate(credential=credential)

    try:
        if is_authenticated:
            logger.info("Request is authenticated")
            response = generate_policy("user", "Allow", event["methodArn"])
        else:
            logger.info("Request is not authenticated")
            response = generate_policy("user", "Deny", event["methodArn"])

        return json.loads(response)

    except Exception as exec_code:
        return {"statusCode": 500, "body": str(exec_code)}
