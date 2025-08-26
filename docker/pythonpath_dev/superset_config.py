# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache
from flask import session, redirect, g, request

from flask_appbuilder import expose, IndexView

from superset.extensions import (
    appbuilder,
)

from superset.utils.core import (
    get_user_id,
)

from superset.superset_typing import FlaskResponse

# import for keycloak
import jwt
from flask_appbuilder.security.manager import AUTH_OAUTH
from superset.security import SupersetSecurityManager

logger = logging.getLogger()

def get_locale():
    x = session["locale"]

    logger.info(f"session language is: {x}")

    return x

JINJA_CONTEXT_ADDONS = {
    'get_locale': get_locale,
}

# ---------------------------------------------------
# Babel config for translations
# ---------------------------------------------------
# Setup default language
BABEL_DEFAULT_LOCALE = "en"
# Your application default translation path
BABEL_DEFAULT_FOLDER = "superset/translations"
# The allowed translation for your app
LANGUAGES = {
    "en": {"flag": "us", "name": "English"},
    "ru": {"flag": "ru", "name": "Russian"}
}

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 5,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG


CELERY_CONFIG = None

FEATURE_FLAGS = {"ALERT_REPORTS": False,
                 "ENABLE_TEMPLATE_PROCESSING": True,
                 "DASHBOARD_RBAC": True,
                 "HORIZONTAL_FILTER_BAR": True,
                 "TAGGING_SYSTEM": True}
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = "http://superset:8088/"
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = WEBDRIVER_BASEURL
HTML_SANITIZATION = False
TALISMAN_ENABLED = False
SQLALCHEMY_POOL_SIZE = 70
SQLALCHEMY_MAX_OVERFLOW = 70
SQLALCHEMY_POOL_TIMEOUT = 30

PREVIOUS_SECRET_KEY = "TEST_NON_DEV_SECRET"
SECRET_KEY = "PROD_NON_DEV_SECRET"

SQLLAB_CTAS_NO_LIMIT = True


# # keycloak integration

#AUTH_TYPE = AUTH_OAUTH

# registration configs
AUTH_USER_REGISTRATION = True  # allow registration users who are not already in the FAB DB
AUTH_USER_REGISTRATION_ROLE = "Public"  # this role will be given in addition to any AUTH_ROLES_MAPPING
AUTH_ROLES_SYNC_AT_LOGIN = True # always check roles on login, not only on registration

# the list of providers which the user can choose from
host_keycloak = "1.1.1.1"
port_keycloak = "8080"
realm = "master"
client_secret = "blabla"
client_id = "Superset"
OAUTH_PROVIDERS = [
    {
        "name": "keycloak",
        "icon": "fa-key",
        "token_key": "access_token",
        "remote_app": {
            "client_id": f"{client_id}", # change to your client id
            "client_secret": f"{client_secret}", # change to your client secret
            "api_base_url": f"http://{host_keycloak}:{port_keycloak}/realms/{realm}/protocol/openid-connect", # change to your domain and realm
            "client_kwargs": {
                "scope": "openid profile email roles",
                "roles_key": "realm_access.roles",
                "token_endpoint_auth_method": "client_secret_post"
            },
            "server_metadata_url": f"http://{host_keycloak}:{port_keycloak}/realms/{realm}/.well-known/openid-configuration", # change to your domain
            "access_token_url": f"http://{host_keycloak}:{port_keycloak}/realms/{realm}/protocol/openid-connect/token", # change to your domain
            "authorize_url": f"http://{host_keycloak}:{port_keycloak}/realms/{realm}/protocol/openid-connect/auth", # change to your domain
            "request_token_url": None,
        },
    },
]

AUTH_ROLES_MAPPING = {
"KeyCloakSupersetAdmin": ["Admin"]
}

class CustomSsoSecurityManager(SupersetSecurityManager):

    def oauth_user_info(self, provider, response=None):
        #logging.debug("Oauth2 provider: {0}.".format(provider))
        if provider == 'keycloak':
            #logging.info("keycloak - LOGIN")
            me = self.appbuilder.sm.oauth_remotes[provider].get('openid-connect/userinfo')
            me.raise_for_status()
            me_data = me.json()
            #logging.debug(f"user_data from keycloack: {me_data}")
            #logging.debug(f"response from keycloack: {response}")
            # in access_token life roles for user
            access_token = response.get("access_token")
            decoded_access_token = jwt.decode(access_token, options={"verify_signature": False})
            #logging.debug(f"decoded_access_token: {decoded_access_token}")
            roles = decoded_access_token.get("realm_access").get("roles")
            return { 'username' : me_data['preferred_username']
                    , 'first_name' : me_data['given_name']
                    , 'last_name' : me_data['family_name']
                    , 'role_keys': roles
                    }

#CUSTOM_SECURITY_MANAGER = CustomSsoSecurityManager

# custom welcome page
class SupersetIndexView(IndexView):
    @expose("/")
    def index(self) -> FlaskResponse:
        if not g.user or not get_user_id():
            # Do steps for anonymous user e.g.
            return redirect("/login")
        # Do steps for authenticated user e.g.
        return redirect("/superset/dashboard/1")


FAB_INDEX_VIEW = f"{SupersetIndexView.__module__}.{SupersetIndexView.__name__}"

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at " f"[{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
