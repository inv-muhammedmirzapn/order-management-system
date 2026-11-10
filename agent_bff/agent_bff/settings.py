import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Ensure local project root is on sys.path for local generated/ imports
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SECRET_KEY = os.getenv('SECRET_KEY', 'agent-bff-insecure-key-for-operations-development-456')
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'rest_framework',
    'agent_orders',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'agent_bff.urls'

# The BFF is a stateless gRPC gateway and does not use a database
DATABASES = {}

REST_FRAMEWORK = {
    'UNAUTHENTICATED_USER': None,
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'

# Agent Order Management gRPC Service Endpoint
AGENT_ORDER_GRPC_HOST = os.getenv('AGENT_ORDER_GRPC_HOST', os.getenv('ORDER_GRPC_HOST', 'localhost:50052'))


