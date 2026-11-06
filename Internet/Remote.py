"""
Remote.py - control your other machines on your own LAN.

  On the machine you want to control:   listen
  On the machine you control from:      exec  ->  connect  ->  pick a number

Security model (read this):
  * The receiver only starts when YOU type 'listen', runs in the foreground,
    and prints every command it executes. Ctrl+C stops it.
  * Every connection must prove it knows the shared password
    (HMAC challenge-response, the password is never sent).
  * Every message is authenticated (HMAC + counter), so nobody on the
    network can inject or replay commands in a session.
  * Only private/LAN addresses are accepted. 5 wrong passwords = 60s lockout.
  * The traffic is NOT encrypted: someone sniffing your network could read
    command output. Fine for a trusted home LAN; for anything else use SSH.
"""

import contextlib
import getpass
import hashlib
import hmac
import io
import ipaddress
import json
import os
import platform
import secrets
import shlex
import socket
import struct
import threading
import time

import System.Kernel as Kernel

DISCOVERY_PORT = 50505
TCP_PORT = 50506
DISCOVERY_MAGIC = b"MILADSHELL-DISCOVER-1"
PROTOCOL_TAG = b"MSH1"

MAX_MESSAGE = 2 * 1024 * 1024       # max size of one protocol message
MAX_OUTPUT = 1024 * 1024            # max command output sent back
MIN_PASSWORD_LENGTH = 8
MAX_FAILURES = 5
LOCKOUT_SECONDS = 60
HANDSHAKE_TIMEOUT = 10
IDLE_TIMEOUT = 900                  # server drops silent clients after 15 min
COMMAND_TIMEOUT = 300               # client waits this long for a result

# Commands that make no sense (or are unsafe) to run through a remote session.
REMOTE_BLOCKED = {"clear", "exec", "listen", "exit"}


class ProtocolError(Exception):
    pass


# ---------------------------------------------------------------------------
# Crypto / framing helpers
# ---------------------------------------------------------------------------

def _derive_key(password):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), b"MiladMA87-Shell-v1", 200_000
    )


def _mac(key, *parts):
    h = hmac.new(key, digestmod=hashlib.sha256)
    for part in parts:
        h.update(len(part).to_bytes(4, "big"))
        h.update(part)
    return h.digest()


def _recv_exact(sock, size):
    buffer = bytearray()
    while len(buffer) < size:
        chunk = sock.recv(size - len(buffer))
        if not chunk:
            raise ConnectionError("connection closed")
        buffer += chunk
    return bytes(buffer)


class _Channel:
    """Authenticated message channel: [length][MAC][json payload]."""

    def __init__(self, sock, session_key, role):
        self.sock = sock
        self.key = session_key
        self.send_role = role
        self.recv_role = b"S" if role == b"C" else b"C"
        self.send_counter = 0
        self.recv_counter = 0

    def send(self, message):
        payload = json.dumps(message).encode("utf-8")
        if len(payload) > MAX_MESSAGE:
            raise ProtocolError("message too large")
        tag = _mac(self.key, self.send_role,
                   self.send_counter.to_bytes(8, "big"), payload)
        self.send_counter += 1
        self.sock.sendall(struct.pack(">I", len(payload)) + tag + payload)

    def receive(self):
        header = _recv_exact(self.sock, 4 + 32)
        length = struct.unpack(">I", header[:4])[0]
        if length > MAX_MESSAGE:
            raise ProtocolError("message too large")
        tag = header[4:]
        payload = _recv_exact(self.sock, length)
        expected = _mac(self.key, self.recv_role,
                        self.recv_counter.to_bytes(8, "big"), payload)
        if not hmac.compare_digest(tag, expected):
            raise ProtocolError("message authentication failed")
        self.recv_counter += 1
        return json.loads(payload.decode("utf-8"))


def _is_lan_address(address):
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


# ---------------------------------------------------------------------------
# Receiver (server) side
# ---------------------------------------------------------------------------

_failures = {}   # ip -> [failed_count, locked_until_timestamp]


def _is_locked(ip):
    entry = _failures.get(ip)
    return bool(entry and entry[1] > time.time())


def _register_failure(ip):
    entry = _failures.setdefault(ip, [0, 0.0])
    entry[0] += 1
    if entry[0] >= MAX_FAILURES:
        entry[0] = 0
        entry[1] = time.time() + LOCKOUT_SECONDS
        print(f"[!] {ip} locked out for {LOCKOUT_SECONDS}s (too many failures)")
    time.sleep(1)   # slows down password guessing


def _server_handshake(conn, key):
    """Return the session key, or None if the client failed authentication."""
    try:
        server_nonce = secrets.token_bytes(16)
        conn.sendall(PROTOCOL_TAG + server_nonce)

        data = _recv_exact(conn, 16 + 32)
        client_nonce, proof = data[:16], data[16:]

        expected = _mac(key, b"C", server_nonce, client_nonce)
        if not hmac.compare_digest(proof, expected):
            return None

        conn.sendall(_mac(key, b"S", client_nonce, server_nonce))
        return _mac(key, b"session", server_nonce, client_nonce)

    except (OSError, ConnectionError):
        return None


def _execute_line(run_argv, line):
    """Run one command line and return everything it printed."""
    try:
        argv = shlex.split(line)
    except ValueError:
        return "Error: invalid syntax (unclosed quote?)\n"

    if not argv:
        return ""

    if argv[0].lower() in REMOTE_BLOCKED:
        return f"'{argv[0]}' is not available in a remote session.\n"

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        try:
            run_argv(argv)
        except Exception as error:
            print(f"Unexpected error: {error}")

    output = buffer.getvalue()
    if len(output) > MAX_OUTPUT:
        output = output[:MAX_OUTPUT] + "\n[output truncated]\n"
    return output


def _serve_session(conn, address, key, run_argv):
    ip = address[0]

    conn.settimeout(HANDSHAKE_TIMEOUT)
    session_key = _server_handshake(conn, key)
    if session_key is None:
        print(f"[!] {ip} failed authentication")
        _register_failure(ip)
        return

    _failures.pop(ip, None)
    print(f"[+] {ip} authenticated")

    channel = _Channel(conn, session_key, b"S")
    conn.settimeout(IDLE_TIMEOUT)
    channel.send({"type": "hello", "host": socket.gethostname(), "cwd": os.getcwd()})

    while True:
        message = channel.receive()
        kind = message.get("type")

        if kind == "bye":
            break
        if kind != "cmd":
            continue

        line = str(message.get("line", ""))
        print(f"[{ip}] > {line}")
        output = _execute_line(run_argv, line)
        channel.send({"type": "result", "output": output, "cwd": os.getcwd()})


def _discovery_responder(stop_event):
    """Answer 'who is listening?' broadcasts so clients can find this machine."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(1.0)
    except OSError as error:
        print(f"[!] Discovery disabled ({error}); clients must use 'connect <ip>'")
        return

    reply = json.dumps({
        "name": socket.gethostname(),
        "port": TCP_PORT,
        "os": platform.system(),
    }).encode("utf-8")

    with sock:
        while not stop_event.is_set():
            try:
                data, address = sock.recvfrom(256)
            except socket.timeout:
                continue
            except OSError:
                break

            if data == DISCOVERY_MAGIC and _is_lan_address(address[0]):
                try:
                    sock.sendto(reply, address)
                except OSError:
                    pass


def listen(path=None):
    """Receive remote commands from your other machines. Usage: listen"""
    password = os.environ.get("MILAD_REMOTE_PASSWORD")
    if not password:
        password = getpass.getpass("Set a password for this receiver: ")
        if getpass.getpass("Repeat password: ") != password:
            print("Error: passwords do not match")
            return False

    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Error: password must be at least {MIN_PASSWORD_LENGTH} characters")
        return False

    key = _derive_key(password)

    # Imported here (not at the top) to avoid a circular import.
    from Dispatcher import run_argv

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", TCP_PORT))
        server.listen(1)
        server.settimeout(1.0)   # lets Ctrl+C work on Windows too
    except OSError as error:
        print(f"Error: cannot listen on port {TCP_PORT}: {error}")
        server.close()
        return False

    stop_event = threading.Event()
    threading.Thread(target=_discovery_responder, args=(stop_event,), daemon=True).start()

    original_dir = os.getcwd()
    print(f"Receiver '{socket.gethostname()}' is waiting on port {TCP_PORT}.")
    print("Every executed command is shown here. Press Ctrl+C to stop.\n")

    try:
        while True:
            try:
                conn, address = server.accept()
            except socket.timeout:
                continue

            ip = address[0]
            with conn:
                if not _is_lan_address(ip):
                    print(f"[!] rejected non-LAN address {ip}")
                    continue
                if _is_locked(ip):
                    continue

                try:
                    _serve_session(conn, address, key, run_argv)
                except (OSError, ConnectionError, ProtocolError,
                        ValueError, socket.timeout) as error:
                    print(f"[!] session with {ip} ended: {error}")
                else:
                    print(f"[-] {ip} disconnected")
                finally:
                    os.chdir(original_dir)

    except KeyboardInterrupt:
        print("\nReceiver stopped.")
    finally:
        stop_event.set()
        server.close()
        os.chdir(original_dir)

    return True


# ---------------------------------------------------------------------------
# Controller (client) side
# ---------------------------------------------------------------------------

def _discover(wait=2.0):
    """Broadcast on the LAN and return the receivers that answered."""
    found = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.3)

        deadline = time.time() + wait
        last_send = 0.0
        while time.time() < deadline:
            if time.time() - last_send > 0.7:     # UDP can drop packets, resend
                try:
                    sock.sendto(DISCOVERY_MAGIC, ("255.255.255.255", DISCOVERY_PORT))
                except OSError:
                    pass
                last_send = time.time()

            try:
                data, address = sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                info = json.loads(data.decode("utf-8"))
                found[address[0]] = {
                    "ip": address[0],
                    "name": str(info.get("name", "?")),
                    "port": int(info.get("port", TCP_PORT)),
                    "os": str(info.get("os", "?")),
                }
            except (ValueError, UnicodeError, TypeError):
                continue
    finally:
        sock.close()

    return list(found.values())


def _open_channel(ip, port, password):
    """Connect + authenticate. Returns a ready _Channel (socket is channel.sock)."""
    key = _derive_key(password)
    sock = socket.create_connection((ip, port), timeout=5)

    try:
        hello = _recv_exact(sock, len(PROTOCOL_TAG) + 16)
        if hello[:len(PROTOCOL_TAG)] != PROTOCOL_TAG:
            raise ProtocolError("this is not a MiladMA87 receiver")
        server_nonce = hello[len(PROTOCOL_TAG):]

        client_nonce = secrets.token_bytes(16)
        sock.sendall(client_nonce + _mac(key, b"C", server_nonce, client_nonce))

        try:
            server_proof = _recv_exact(sock, 32)
        except ConnectionError:
            raise ProtocolError("authentication failed (wrong password or locked out)")

        if not hmac.compare_digest(server_proof, _mac(key, b"S", client_nonce, server_nonce)):
            raise ProtocolError("the receiver could not prove it knows the password")

        channel = _Channel(sock, _mac(key, b"session", server_nonce, client_nonce), b"C")
        sock.settimeout(COMMAND_TIMEOUT)
        return channel

    except Exception:
        sock.close()
        raise


def _remote_shell(channel):
    """Everything typed here is sent to the receiver and executed there."""
    hello = channel.receive()
    host = hello.get("host", "remote")
    cwd = hello.get("cwd", "")

    print(f"\nConnected to {host}.")
    print("Everything you type now runs on that machine.")
    print("Type 'disconnect' to come back, 'clear' clears your screen.\n")

    try:
        while True:
            try:
                line = input(f"[{host}] {cwd} >--> ").strip()
            except EOFError:
                break

            if not line:
                continue

            lowered = line.lower()
            if lowered in ("disconnect", "exit"):
                break
            if lowered == "clear":
                Kernel.clear()
                continue

            channel.send({"type": "cmd", "line": line})
            reply = channel.receive()
            output = reply.get("output", "")
            if output:
                print(output, end="" if output.endswith("\n") else "\n")
            cwd = reply.get("cwd", cwd)
            print()

        channel.send({"type": "bye"})

    except KeyboardInterrupt:
        print("\nDisconnected.")
    except (OSError, ConnectionError, ProtocolError, ValueError, socket.timeout) as error:
        print(f"\nConnection lost: {error}")
    finally:
        channel.sock.close()
        print(f"Disconnected from {host}.")


def _connect_flow(args):
    if args:
        target = {"ip": args[0], "name": args[0], "port": TCP_PORT}
    else:
        print("Searching for receivers on your network...")
        receivers = _discover()
        if not receivers:
            print("No receiver found. Is 'listen' running on the other machine?")
            print("You can also connect directly: connect <ip>")
            return False

        print()
        for number, receiver in enumerate(receivers, start=1):
            print(f"  {number}) {receiver['name']:<25} {receiver['ip']:<16} {receiver['os']}")
        print()

        try:
            choice = input("Enter a number (empty to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return False

        if not choice:
            return False
        if not choice.isdigit() or not 1 <= int(choice) <= len(receivers):
            print("Error: invalid number")
            return False

        target = receivers[int(choice) - 1]

    try:
        password = getpass.getpass(f"Password for {target['name']}: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False

    try:
        channel = _open_channel(target["ip"], target["port"], password)
    except (OSError, ProtocolError, socket.timeout) as error:
        print(f"Error: {error}")
        return False

    _remote_shell(channel)
    return True


def execMode(path=None):
    """Remote control mode. Usage: exec"""
    print("Remote mode. Commands: connect [ip] | help | exit")

    while True:
        try:
            line = input("exec> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return True

        if not line:
            continue

        parts = line.split()
        command, args = parts[0].lower(), parts[1:]

        if command == "exit":
            return True
        elif command == "connect":
            _connect_flow(args)
        elif command == "help":
            print("\tconnect\t\t->\tsearch the LAN for receivers and pick one")
            print("\tconnect <ip>\t->\tconnect directly to an IP address")
            print("\texit\t\t->\tleave remote mode")
        else:
            print("unknown command... (use 'connect' or 'exit')")

        print()


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
