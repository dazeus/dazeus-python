#!/usr/bin/env python3

import socket

class DaZeus:
    def __init__(self, addr):
        if ':' not in addr:
            raise AttributeError("Invalid address specified, expected: unix:/path/to/file or tcp:host:port")

        [proto, location] = addr.split(':', 1)

        if proto == 'unix':
            try:
                socket.AF_UNIX
            except NameError:
                raise OSError("Unix sockets are not supported on this platform")

            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(location)
        elif proto == 'tcp':
            if ':' not in location:
                raise AttributeError("No port specified for TCP socket")

            [host, port] = location.split(':', 1)

            if not port.isdigit():
                raise AttributeError("Port specified is not numeric")

            port = int(port)
            if port < 1 or port > 65536:
                raise AttributeError("Port not in range")

            self.sock = socket.create_connection((host, port))
        else:
            raise AttributeError("Invalid protocol specified, must use unix or tcp")

        self.buffer = b''

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.sock.close()

    def check_message(self):
        offset = 0
        message_len = 0

        while offset < len(self.buffer):
            curr = self.buffer[offset]
            if curr >= ord('0') and curr <= ord('9'):
                message_len *= 10
                message_len += curr - ord('0')
                offset += 1
            elif curr == ord('\n') or curr == ord('\r'):
                offset += 1
            else:
                break

        if message_len > 0 and len(self.buffer) >= offset + message_len:
            return (offset, message_len)
        else:
            return (None, None)

    def read(self):
        while True:
            (offset, message_len) = self.check_message()
            if message_len is not None:
                return self.buffer[offset:offset+message_len].decode('utf-8')
            self.buffer += self.sock.recv(1024)

    def write(self, msg):
        bytemsg = msg.encode('utf-8')
        totalsent = 0
        while totalsent < len(bytemsg):
            sent = self.sock.send(bytemsg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent += sent
