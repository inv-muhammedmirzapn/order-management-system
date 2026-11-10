#!/usr/bin/env python
"""
Standalone entry point for running the AgentOrderService gRPC server.
Initializes Django and starts the gRPC service on port 50052.
"""
import os
import sys
from concurrent import futures
from pathlib import Path
import grpc

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agent_service.settings')
import django
django.setup()

from generated import agent_order_pb2_grpc
from orders.grpc_service import AgentOrderGrpcServicer


def serve():
    port = os.getenv('PORT', os.getenv('AGENT_ORDER_GRPC_PORT', '50052'))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agent_order_pb2_grpc.add_AgentOrderServiceServicer_to_server(
        AgentOrderGrpcServicer(), server
    )
    bind_address = f"[::]:{port}"
    server.add_insecure_port(bind_address)
    server.start()
    print(f"AgentOrderService gRPC server running at {bind_address}")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()

