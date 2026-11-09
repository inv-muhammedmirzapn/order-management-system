#!/usr/bin/env python
"""
Compile Protocol Buffer definitions into Python gRPC code.
Usage:
    python generate_proto.py
"""
import sys
from pathlib import Path
from importlib import resources
from grpc_tools import protoc

ROOT_DIR = Path(__file__).resolve().parent
PROTO_DIR = ROOT_DIR / "proto"
GENERATED_DIR = ROOT_DIR / "generated"


def generate_for_target(output_dir: Path, proto_file: Path, proto_include: str):
    output_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "grpc_tools.protoc",
        f"-I{PROTO_DIR}",
        f"-I{proto_include}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        str(proto_file),
    ]

    ret = protoc.main(args)
    if ret != 0:
        print(f"Error: protoc returned exit code {ret}", file=sys.stderr)
        sys.exit(ret)

    # Write __init__.py for clean module imports
    init_file = output_dir / "__init__.py"
    init_content = (
        "import sys\n"
        "from pathlib import Path\n\n"
        "_pkg_dir = str(Path(__file__).resolve().parent)\n"
        "if _pkg_dir not in sys.path:\n"
        "    sys.path.insert(0, _pkg_dir)\n\n"
        "from . import order_pb2\n"
        "from . import order_pb2_grpc\n\n"
        '__all__ = ["order_pb2", "order_pb2_grpc"]\n'
    )
    init_file.write_text(init_content)


def main():
    proto_file = PROTO_DIR / "order.proto"
    if not proto_file.exists():
        print(f"Error: {proto_file} not found!", file=sys.stderr)
        sys.exit(1)

    # Locate grpc_tools standard proto includes (e.g., google/protobuf/timestamp.proto)
    proto_include = str((resources.files("grpc_tools") / "_proto").resolve())

    print(f"==> Compiling {proto_file.name}...")

    # Output to generated/ (used by the Django microservice)
    generate_for_target(GENERATED_DIR, proto_file, proto_include)
    print(f"✔ Generated in: {GENERATED_DIR.relative_to(ROOT_DIR)}/")
    print(f"   • {GENERATED_DIR.relative_to(ROOT_DIR)}/order_pb2.py")
    print(f"   • {GENERATED_DIR.relative_to(ROOT_DIR)}/order_pb2_grpc.py")

    print("\n==> Proto generation completed successfully!")


if __name__ == "__main__":
    main()
