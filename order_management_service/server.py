#!/usr/bin/env python
"""
Standalone entry point for running the gRPC server.
Initializes Django and starts the gRPC service.
"""
import os
import sys
from concurrent import futures
from pathlib import Path
import grpc

# Add project root to Python path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'order_service.settings')
import django
django.setup()

from generated import order_pb2_grpc
from orders.grpc_service import OrderGrpcServicer


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_pb2_grpc.add_OrderServiceServicer_to_server(OrderGrpcServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("OrderService gRPC server running at [::]:50051")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
