import streamlit as st
import streamlit_authenticator as stauth
import os
import yaml
from yaml.loader import SafeLoader


def setup_authenticator():
    """
    Sets up the Streamlit Authenticator using environment variables.
    Returns the authenticator object.
    """
    # Get configuration from environment variables
    # Default to 'admin'/'admin' if not set (ONLY FOR DEV/FALLBACK)
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    auth_secret = os.getenv("AUTH_SECRET", "some_random_secret_key")

    # In a real scenario, we might want to hash the password if it's not already hashed.
    # streamlit-authenticator expects hashed passwords in the config.
    # However, to make it easy to use with Env Vars (where you might pass plain text),
    # we can hash it here dynamically.

    # Note: stauth.Hasher.hash_list expects a list of passwords
    hashed_passwords = stauth.Hasher.hash_list([admin_password])

    # Construct the configuration dictionary
    config = {
        "credentials": {
            "usernames": {
                admin_user: {
                    "name": "Admin",
                    "password": hashed_passwords[0],
                    "email": "admin@example.com",  # Dummy email
                }
            }
        },
        "cookie": {
            "expiry_days": 30,
            "key": "random_signature_key",  # This should ideally also be secret, but fixed for now
            "name": "clinical_extractor_auth",
        },
        "preauthorized": {"emails": []},
    }

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        preauthorized=config["preauthorized"],
    )

    return authenticator
