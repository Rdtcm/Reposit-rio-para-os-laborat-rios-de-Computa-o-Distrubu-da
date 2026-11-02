"""Cliente CLI: upload e download incremental, com publicacao atomica da saida."""
import argparse
import os
from pathlib import Path
import tempfile
import sys
import grpc
import file_processor_pb2 as pb
import file_processor_pb2_grpc as rpc

METHODS = {"compress": "CompressPDF", "text": "ConvertToTXT",
           "convert": "ConvertImageFormat", "resize": "ResizeImage"}

def transfer(stub, operation, source, destination, output_format="", width=0, height=0):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("Entrada e saida devem ser diferentes")
    # Abrir antes da RPC para que arquivo ausente seja um erro local claro.
    with source.open("rb") as incoming:
        def requests():
            yield pb.FileRequest(metadata=pb.Metadata(file_name=source.name,
                output_format=output_format, width=width, height=height))
            while chunk := incoming.read(65536):
                yield pb.FileRequest(content=chunk)
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".download-", suffix=".part", dir=destination.parent)
        try:
            responses = getattr(stub, METHODS[operation])(requests(), timeout=60)
            count = 0
            with os.fdopen(fd, "wb") as outgoing:
                for response in responses:
                    outgoing.write(response.content)
                    count += 1
            if not count:
                raise RuntimeError("Servidor retornou resposta vazia")
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return destination.stat().st_size

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default=os.getenv("GRPC_SERVER", "localhost:50051"))
    parser.add_argument("operation", choices=[*METHODS, "health"])
    parser.add_argument("input", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--format", default="png")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    args = parser.parse_args()
    if args.operation != "health" and (not args.input or not args.output):
        parser.error("Informe os caminhos de entrada e saida")
    try:
        with grpc.insecure_channel(args.server) as channel:
            grpc.channel_ready_future(channel).result(timeout=20)
            stub = rpc.FileProcessorServiceStub(channel)
            if args.operation == "health":
                print(stub.Health(pb.HealthRequest(), timeout=5).status)
            else:
                size = transfer(stub, args.operation, args.input, args.output, args.format, args.width, args.height)
                print(f"OK {METHODS[args.operation]}: {args.output} ({size} bytes)")
        return 0
    except grpc.RpcError as exc:
        print(f"Erro gRPC {exc.code().name}: {exc.details()}", file=sys.stderr)
    except grpc.FutureTimeoutError:
        print("Erro: servidor indisponivel", file=sys.stderr)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Erro local: {exc}", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
