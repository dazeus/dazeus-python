from .scope import Scope
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
        handle = self._add_listener({
            'event': event,
            'handler': handler
        })

        self._write({
            "do": "subscribe",
            "params": [event]
        })
        self._wait_success_response()
        return handle

    def subscribe_command(self, command, handler, scope = Scope()):
        handle = self._add_listener({
            'event': 'COMMAND',
            'command': command,
            'handler': handler
        })

        self._write({
            "do": "command",
            "params": [command] + scope.to_command_list()
        })
        self._wait_success_response()
        return handle

    def unsubscribe(self, id):
        self._listeners = [l for l in self._listeners if l['id'] != id]

    def _handle_event(self, event):
        for l in self._listeners:
            if l['event'] != event['event'] or \
               (event['event'] == 'COMMAND' and event['params'][3] != l['command']):
                continue

            l['handler'](event)

    def _wait_response(self):
        while True:
            msg = self._read()
            if 'event' in msg:
                self._handle_event(msg)
            else:
                return msg

    def _wait_success_response(self):
        resp = self._wait_response()
        if 'error' in resp:
            raise RuntimeError(resp['error'])
        return resp

    def listen(self):
        while True:
            msg = self._read()
            if 'event' in msg:
                self._handle_event(msg)
            else:
                raise RuntimeError("Got response to unsent request")

    def networks(self):
        self._write({"get": "networks"})
        return self._wait_success_response()

    def channels(self, network):
        self._write({"get": "channels", "params": [network]})
        return self._wait_success_response()

    def join(self, network, channel):
        self._write({"do": "join", "params": [network, channel]})
        return self._wait_success_response()

    def part(self, network, channel):
        self._write({"do": "part", "params": [network, channel]})
        return self._wait_success_response()

    def message(self, network, channel, message):
        self._write({"do": "message", "params": [network, channel, message]})
        return self._wait_success_response()

    def action(self, network, channel, message):
        self._write({"do": "action", "params": [network, channel, message]})
        return self._wait_success_response()

    def notice(self, network, channel, message):
        self._write({"do": "notice", "params": [network, channel, message]})
        return self._wait_success_response()

    def reply(self, network, channel, sender, message, highlight = False, type = 'message'):
        raise NotImplementedError()

    def ctcp(self, network, channel, message):
        self._write({"do": "ctcp", "params": [network, channel, message]})
        return self._wait_success_response()

    def ctcp_reply(self, network, channel, message):
        self._write({"do": "ctcp_rep", "params": [network, channel, message]})
        return self._wait_success_response()

    def nick(self, network):
        self._write({"get": "nick", "params": [network]})
        return self._wait_success_response()

    def get_config(self, key, group = 'plugin'):
        self._write({"get": "config", "params": [group, key]})
        return self._wait_success_response()

    def highlight_character(self):
        return self.get_config('highlight', 'core')

    def get_property(self, property, scope):
        raise NotImplementedError()

    def set_property(self, property, value, scope):
        raise NotImplementedError()

    def unset_property(self, property, scope):
        raise NotImplementedError()

    def property_keys(self, scope):
        raise NotImplementedError()

    def get_permission(self, permission, scope, allow = True):
        raise NotImplementedError()

    def set_permission(self, permission, scope, allow = True):
        raise NotImplementedError()

    def remove_permission(self, permission, scope):
        raise NotImplementedError()

    def whois(self, network, nick):
        raise NotImplementedError()

    def names(self, network, channel):
        raise NotImplementedError()

    def nicknames(self, network, channel):
        raise NotImplementedError()
