"""Packaged backend entry point, listening only on an ephemeral loopback port."""
import json
import socket
import sys
import threading
import uvicorn


def main():
    # Import after Electron provides the profile's paths and API credentials.
    from backend.main import app
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level='warning', access_log=False))
    def listen():
        for line in sys.stdin:
            if line.strip() == 'STOP':
                server.should_exit = True
                break
        # The parent app may terminate unexpectedly and close the pipe.
        server.should_exit = True
    threading.Thread(target=listen, daemon=True).start()
    print('DESKTOP_READY:' + json.dumps({'port': port}), flush=True)
    server.run(sockets=[sock])


if __name__ == '__main__':
    main()
