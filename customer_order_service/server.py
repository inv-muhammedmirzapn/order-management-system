#!/usr/bin/env python
"""
Standalone entry point for running the CustomerOrderService gRPC server.
Initializes Django and starts the gRPC service on port 50051.
"""
import os
import sys
from concurrent import futures
from pathlib import Path
import grpc

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'customer_service.settings')
import django
django.setup()

from generated import customer_order_pb2_grpc
from orders.grpc_service import CustomerOrderGrpcServicer


def serve():
    port = os.getenv('PORT', os.getenv('CUSTOMER_ORDER_GRPC_PORT', '50051'))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    customer_order_pb2_grpc.add_CustomerOrderServiceServicer_to_server(
        CustomerOrderGrpcServicer(), server
    )
    bind_address = f"[::]:{port}"
    server.add_insecure_port(bind_address)
    server.start()
    print(f"CustomerOrderService gRPC server running at {bind_address}")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()

