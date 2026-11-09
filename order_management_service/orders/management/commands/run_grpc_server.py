import signal
import sys
import time
from concurrent import futures
import grpc
from django.core.management.base import BaseCommand
from generated import order_pb2_grpc
from orders.grpc_service import OrderGrpcServicer


class Command(BaseCommand):
    help = "Run the Order Management gRPC microservice server."

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=50051,
            help='Port to bind the gRPC server (default: 50051)',
        )
        parser.add_argument(
            '--host',
            type=str,
            default='0.0.0.0',
            help='Host interface to bind the gRPC server (default: 0.0.0.0)',
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=10,
            help='Maximum number of thread pool workers (default: 10)',
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        workers = options['workers']
        bind_address = f"{host}:{port}"

        self.stdout.write(self.style.SUCCESS(f"Starting gRPC server on {bind_address} (workers: {workers})..."))

        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=workers),
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ],
        )

        order_pb2_grpc.add_OrderServiceServicer_to_server(OrderGrpcServicer(), server)
        server.add_insecure_port(bind_address)
        server.start()

        self.stdout.write(self.style.SUCCESS(f"OrderService gRPC server running at {bind_address}"))

        def handle_shutdown(signum, frame):
            self.stdout.write(self.style.WARNING("\nShutting down gRPC server gracefully..."))
            stop_event = server.stop(grace=5)
            stop_event.wait(timeout=5)
            self.stdout.write(self.style.SUCCESS("gRPC server stopped."))
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        try:
            while True:
                time.sleep(86400)
        except KeyboardInterrupt:
            handle_shutdown(None, None)

