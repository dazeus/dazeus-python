#!/usr/bin/env python3

import socket
import json

class DaZeus:
    def __init__(self, addr, debug = False):
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

        self._buffer = b''
        self._listeners = []
        self._latest_listener_id = 0

        self.debug = debug

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.sock.close()

    def _check_message(self):
        offset = 0
        message_len = 0

        while offset < len(self._buffer):
            curr = self._buffer[offset]
            if curr >= ord('0') and curr <= ord('9'):
                message_len *= 10
                message_len += curr - ord('0')
                offset += 1
            elif curr == ord('\n') or curr == ord('\r'):
                offset += 1
            else:
                break

        if message_len > 0 and len(self._buffer) >= offset + message_len:
            return (offset, message_len)
        else:
            return (None, None)

    def _read(self):
        while True:
            (offset, message_len) = self._check_message()
            if message_len is not None:
                strmsg = self._buffer[offset:offset+message_len].decode('utf-8')
                if self.debug:
                    print("Received message: {0}".format(strmsg))

                msg = json.loads(strmsg)
                self._buffer = self._buffer[offset+message_len:]
                return msg

            self._buffer += self.sock.recv(1024)

    def _write(self, msg):
        strmsg = json.dumps(msg)
        if self.debug:
            print("Sending message: {0}".format(strmsg))

        bytemsg = strmsg.encode('utf-8')
        bytemsg = str(len(bytemsg)).encode('utf-8') + bytemsg
        totalsent = 0
        while totalsent < len(bytemsg):
            sent = self.sock.send(bytemsg[totalsent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            totalsent += sent

    def _add_listener(self, listener):
        listener['id'] = self._latest_listener_id
        self._listeners.append(listener)
        self._latest_listener_id += 1
        return listener['id']

    def subscribe(self, event, handler):
        return self._add_listener({
            'event': event,
            'handler': handler
        })

    def subscribe_command(self, command, handler):
        return self._add_listener({
            'event': 'command',
            'command': command,
            'handler': handler
        })

    def unsubscribe(self, id):
        self._listeners = [l for l in self._listeners if l['id'] != id]

    def _handle_event(self, event):
        [l['handler'](event) for l in self._listeners if l['event'] == event['event']]

    def _wait_response(self):
        while True:
            msg = self._read()
            if 'event' in msg:
                self._handle_event(msg)
            else:
                return msg

    def listen(self):
        while True:
            msg = self._read()
            if 'event' in msg:
                self._handle_event(msg)
            else:
                raise RuntimeError("Got response to unsent request")

    def networks(self):
        self._write({"get":"networks"})
        return self._wait_response()
