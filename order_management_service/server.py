#!/usr/bin/env python
"""
Standalone entry point for running the gRPC server.
Initializes Django and starts the gRPC service.
"""
import os
import sys
from pathlib import Path

# Add project root and generated folder to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order_service.settings')
import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].isdigit() else "50051"
    call_command('run_grpc_server', port=port)

