import logging
import os
import re
import socket
import ssl
import string
import threading
import time
from base64 import b64encode
from contextlib import contextmanager
from typing import Callable
import requests

from .models import constants
from .models.errors import AuthenticationError, ConnectionLostError, TokenExpiredError
from .core import parser, stanza, types
from .utils import util

logger = logging.getLogger("todlib")

class ToDusClient:
    def __init__(
        self,
        version_name: str = constants.AUTH_VERSION_NAME,
        version_code: str = constants.AUTH_VERSION_CODE,
    ) -> None:
        self.version_name = version_name
        self.version_code = version_code
        self.session = requests.Session()
        self.session.headers.update({"Accept-Encoding": "gzip"})
        self._xml_parser = parser.IncrementalParser()

    def request_code(self, phone_number: str) -> None:
        headers = {
            "Host": "auth.todus.cu",
            "User-Agent": "ToDus " + self.version_name + " Auth",
            "Content-Type": "application/x-protobuf",
        }
        data = (
            bytes([0x0A, 0x0A])
            + phone_number.encode()
            + bytes([0x12, 0x96, 0x01])
            + util.generate_token(150).encode()
        )
        resp = self.session.post(
            "https://auth.todus.cu/v2/auth/users.reserve",
            data=data,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()

    def validate_code(self, phone_number: str, code: str) -> str:
        headers = {
            "Host": "auth.todus.cu",
            "User-Agent": "ToDus " + self.version_name + " Auth",
            "Content-Type": "application/x-protobuf",
        }
        data = (
            bytes([0x0A, 0x0A])
            + phone_number.encode()
            + bytes([0x12, 0x96, 0x01])
            + util.generate_token(150).encode()
            + bytes([0x1A, 0x06])
            + code.encode()
        )
        resp = self.session.post(
            "https://auth.todus.cu/v2/auth/users.register",
            data=data,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.content
        try:
            if b"`" in content:
                idx = content.index(b"`") + 1
                return content[idx : idx + 96].decode("utf-8")
            return content[5:166].decode("utf-8")
        except UnicodeDecodeError:
            raw = content.decode("latin-1", errors="ignore")
            match = re.search(r"[a-f0-9]{96}", raw)
            if match:
                return match.group(0)
            return "".join(c for c in raw if c in string.printable and c not in "\r\n")[:96]

    def login(self, phone_number: str, password: str) -> str:
        headers = {
            "Host": "auth.todus.cu",
            "user-agent": "ToDus " + self.version_name + " Auth",
            "content-type": "application/x-protobuf",
        }
        data = (
            bytes([0x0A, 0x0A])
            + phone_number.encode()
            + bytes([0x12, 0x96, 0x01])
            + util.generate_token(150).encode()
            + bytes([0x12, 0x60])
            + password.encode()
            + bytes([0x1A, 0x05])
            + self.version_code.encode()
        )
        resp = self.session.post(
            "https://auth.todus.cu/v2/auth/token",
            data=data,
            headers=headers,
            timeout=30,
        )
        if resp.status_code == 403:
            raise AuthenticationError("Credenciales invalidas")
        resp.raise_for_status()
        return "".join([c for c in resp.text if c in string.printable])

    def _connect_xmpp(self) -> ssl.SSLSocket:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        sock = ctx.wrap_socket(socket.socket(socket.AF_INET))
        sock.settimeout(constants.DEFAULT_TIMEOUT)
        sock.connect((constants.XMPP_HOST, constants.XMPP_PORT))
        sock.send(stanza.stream_open().encode())
        return sock

    def _recv_all(self, sock: ssl.SSLSocket) -> str | None:
        data = b""
        while True:
            try:
                chunk = sock.recv(constants.BUFFER_SIZE)
                if not chunk:
                    return None
                data += chunk
                if len(chunk) < constants.BUFFER_SIZE:
                    break
            except socket.timeout:
                break
            except OSError:
                return None
        return data.decode("utf-8", errors="replace")

    def _authstr_from_token(self, token: str) -> tuple[str, bytes]:
        payload = util.jwt_decode_payload(token)
        phone = payload.get("username", "")
        if not phone:
            match = re.search(r"(53\d{8})", token)
            if match:
                phone = match.group(1)
        authstr = b64encode((chr(0) + phone + chr(0) + token).encode("utf-8"))
        return phone, authstr

    def _process_handshake(self, response: str, sock, authstr: bytes, sid: str, state: dict) -> bool:
        phase = state.get("phase", "init")
        if phase == "init":
            if "<stream:features><es xmlns='x2'>" in response:
                sock.send(stanza.sasl_auth(authstr))
                state["phase"] = "auth_sent"
                return True
            if response.startswith("<?xml version='1.0'?><stream:stream"):
                if "<stream:features>" in response:
                    sock.send(stanza.sasl_auth(authstr))
                    state["phase"] = "auth_sent"
                return True
            return True
        if phase == "auth_sent":
            if "<ok xmlns='x2'/>" in response:
                sock.send(stanza.stream_restart().encode())
                state["phase"] = "restream"
                return True
            if "<not-authorized/>" in response:
                raise TokenExpiredError()
            return True
        if phase == "restream":
            if "<stream:features><b1 xmlns='x4'/>" in response:
                sock.send(stanza.bind(sid + "-1").encode())
                state["phase"] = "bind_sent"
                return True
            if response.startswith("<?xml version='1.0'?><stream:stream") and "<stream:features><b1 xmlns='x4'/>" in response:
                sock.send(stanza.bind(sid + "-1").encode())
                state["phase"] = "bind_sent"
                return True
            return True
        if phase == "bind_sent":
            if "t='result' i='" + sid + "-1'>" in response:
                return False
            if "<not-authorized/>" in response:
                raise TokenExpiredError()
            return True
        return True

    def _handshake(self, sock: ssl.SSLSocket, token: str) -> None:
        _, authstr = self._authstr_from_token(token)
        sid = util.generate_token(5)
        state = {"phase": "init"}
        while True:
            response = self._recv_all(sock)
            if response is None:
                raise ConnectionLostError("Servidor cerro conexion durante handshake")
            if response == "":
                continue
            if not self._process_handshake(response, sock, authstr, sid, state):
                return

    def send_message(self, token: str, to_jid: str, body: str) -> None:
        msg = stanza.message(to_jid, body)
        with self._xmpp_session(token) as sock:
            sock.send(msg.encode())

    def listen_messages(self, token: str, callback: Callable[[dict], None]) -> None:
        while True:
            try:
                with self._xmpp_session(token) as sock:
                    self._listen_loop(sock, callback)
            except TokenExpiredError:
                raise
            except (ConnectionLostError, OSError, socket.error):
                time.sleep(15)

    def _listen_loop(self, sock: ssl.SSLSocket, callback: Callable[[dict], None]) -> None:
        stop_event = threading.Event()
        ping_id = util.generate_token(5)
        ka = threading.Thread(
            target=self._keepalive_worker,
            args=(sock, stop_event, ping_id),
            daemon=True,
        )
        ka.start()
        self._xml_parser.reset()
        try:
            while True:
                try:
                    response = self._recv_all(sock)
                except OSError as e:
                    raise ConnectionLostError(e)
                if response is None:
                    raise ConnectionLostError("Servidor cerro conexion")
                if response == "":
                    continue
                stanzas = self._xml_parser.feed(response)
                for msg in stanzas:
                    if msg.get("deleted"):
                        continue
                    if msg.get("body") or msg.get("url") or msg.get("contact_id") or msg.get("sticker_id") or msg.get("video_url"):
                        msg_id = msg.get("id", "")
                        msg_from = msg.get("from", "")
                        if msg_id and msg_from:
                            try:
                                receipt = stanza.receipt(msg_from, msg_id)
                                sock.send(receipt.encode())
                            except Exception:
                                pass
                        callback(msg)
        finally:
            stop_event.set()
            self._xml_parser.reset()

    def _keepalive_worker(self, sock: ssl.SSLSocket, stop: threading.Event, ping_id: str) -> None:
        while not stop.is_set():
            time.sleep(constants.KEEPALIVE_INTERVAL)
            if stop.is_set():
                break
            try:
                sock.send(stanza.ping(ping_id).encode())
            except OSError:
                break

    @contextmanager
    def _xmpp_session(self, token: str):
        sock = self._connect_xmpp()
        try:
            self._handshake(sock, token)
            sock.send(stanza.presence().encode())
            yield sock
        finally:
            try:
                sock.send(stanza.stream_close().encode())
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass

class ToDusClient2(ToDusClient):
    def __init__(self, phone_number: str, password: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.phone_number = phone_number
        self.password = password
        self._token = ""

    def login(self) -> None:
        if not self.password:
            raise AuthenticationError("No hay password")
        self._token = super().login(self.phone_number, self.password)

    def send_message(self, to_phone: str, body: str) -> None:
        if not self._token:
            raise AuthenticationError("No autenticado")
        to_jid = util.build_jid(to_phone)
        super().send_message(self._token, to_jid, body)

    def listen_messages(self, callback: Callable[[dict], None]) -> None:
        if not self._token:
            raise AuthenticationError("No autenticado")
        while True:
            try:
                super().listen_messages(self._token, callback)
            except TokenExpiredError:
                self.login()
            except (ConnectionLostError, OSError, socket.error):
                time.sleep(15)