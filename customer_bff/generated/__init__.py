import sys
from pathlib import Path

_pkg_dir = str(Path(__file__).resolve().parent)
if _pkg_dir not in sys.path:
    sys.path.insert(0, _pkg_dir)

from . import customer_order_pb2
from . import customer_order_pb2_grpc

__all__ = ["customer_order_pb2", "customer_order_pb2_grpc"]
