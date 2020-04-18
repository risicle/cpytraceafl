"A useful tool for feeding input to targets which connect to a TCP 'server'"
import socket
from socketserver import BaseRequestHandler, TCPServer
import time


SERVER_FIRST_CHUNK = True
MAX_DATA_LEN = 2000
CHUNK_WAIT_TIME = 0.015
RECV_SIZE = 4096
CHUNK_SEPARATOR = b"\xde\xad\xbe\xef"


def get_handler(source_path):
    class _TCPListenFeederHandler(BaseRequestHandler):
        _source_path = source_path

        def _receive_data(self):
            recv_len = 0
            try:
                while True:
                    new_len = len(self.request.recv(RECV_SIZE))
                    if not new_len:
                        break
                    recv_len += new_len
            except socket.timeout:
                pass
            print(f"{time.monotonic()} \tReceived {recv_len} B")
            return recv_len

        def handle(self):
            self.request.settimeout(CHUNK_WAIT_TIME)
            self.request.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            with open(self._source_path, "rb") as f:
                data = f.read()

            if MAX_DATA_LEN and len(data) > MAX_DATA_LEN:
                # make sure afl doesnt see this trace as "interesting"
                return
            for i, chunk in enumerate(data.split(CHUNK_SEPARATOR)):
                if (i or not SERVER_FIRST_CHUNK) and self._receive_data() == 0:
                    print(f"{time.monotonic()} \tDone, chunks remaining")
                    break
                print(f"{time.monotonic()} \tSending {len(chunk)} B")
                self.request.sendall(chunk)
            else:
                self._receive_data()
                print(f"{time.monotonic()} \tDone, all chunks sent")


    return _TCPListenFeederHandler


# usage: tcplistenfeeder.py <port> <payload file>
if __name__ == "__main__":
    import sys

    with TCPServer(("127.0.0.1", int(sys.argv[1])), get_handler(sys.argv[2])) as server:
        server.serve_forever()
