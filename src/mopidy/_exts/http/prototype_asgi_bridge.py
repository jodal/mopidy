# /// script
# requires-python = ">=3.13"
# dependencies = ["tornado>=6.5", "starlette", "websockets", "httpx"]
# ///
"""PROTOTYPE. Throwaway code. Do not import.

Question: can Tornado mount an ASGI app on the same port as Tornado apps,
with HTTP and WebSockets, in a non-main thread with its own event loop?

Run: uv run --script src/mopidy/_exts/http/prototype_asgi_bridge.py
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
import traceback
from urllib.parse import unquote

import httpx
import tornado.httpserver
import tornado.iostream
import tornado.netutil
import tornado.routing
import tornado.web
import tornado.websocket
import websockets.asyncio.client
import websockets.exceptions
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute

ASGI = {"version": "3.0", "spec_version": "2.4"}

# ---------------------------------------------------------------------------
# The bridge
# ---------------------------------------------------------------------------


def make_scope(handler: tornado.web.RequestHandler, type_: str, root_path: str):
    request = handler.request
    address = getattr(request.connection.context, "address", None)  # pyright: ignore[reportOptionalMemberAccess]
    client = (address[0], address[1]) if address else (request.remote_ip, 0)
    sockname = request.connection.stream.socket.getsockname()  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
    scheme = request.protocol
    if type_ == "websocket":
        scheme = "wss" if scheme == "https" else "ws"
    return {
        "type": type_,
        "asgi": ASGI,
        "http_version": request.version.removeprefix("HTTP/"),
        "scheme": scheme,
        # Modern ASGI convention: path is the full path, root_path the prefix.
        "path": unquote(request.path),
        "raw_path": request.path.encode("latin-1"),
        "query_string": request.query.encode("latin-1"),
        "root_path": root_path,
        "headers": [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in request.headers.get_all()
        ],
        "client": client,
        "server": sockname[:2],
    }


@tornado.web.stream_request_body
class AsgiHttpHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ("GET", "HEAD", "POST", "DELETE", "PATCH", "PUT", "OPTIONS")

    def initialize(self, app, root_path):
        self.app = app
        self.root_path = root_path

    def compute_etag(self):
        return None  # Do not let Tornado add ETags or 304s to ASGI responses.

    def prepare(self):
        self.receive_queue = asyncio.Queue()
        scope = make_scope(self, "http", self.root_path)
        scope["method"] = self.request.method
        self.response_done = asyncio.get_running_loop().create_future()
        self.app_task = asyncio.ensure_future(self.app(scope, self.receive, self.send))

    def data_received(self, chunk):
        self.receive_queue.put_nowait(
            {"type": "http.request", "body": chunk, "more_body": True}
        )

    async def handle(self, *_args):
        self.receive_queue.put_nowait(
            {"type": "http.request", "body": b"", "more_body": False}
        )
        # Finish when the app sends the last body part. The app task can go on
        # after that, for example to run Starlette background tasks.
        await asyncio.wait(
            [self.response_done, self.app_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not self.response_done.done():
            try:
                self.app_task.result()
            except Exception:
                # For example Starlette's ClientDisconnect after a failed send().
                if self.request.connection.stream.closed():  # pyright: ignore[reportOptionalMemberAccess, reportAttributeAccessIssue]
                    return
                raise
            raise RuntimeError("ASGI app returned without a complete response")
        if not self._finished:
            self.finish()

    get = head = post = delete = patch = put = options = handle

    def on_connection_close(self):
        self.receive_queue.put_nowait({"type": "http.disconnect"})

    async def receive(self):
        return await self.receive_queue.get()

    async def send(self, message):
        if message["type"] == "http.response.start":
            self.clear()
            for name in ("Content-Type", "Server", "Date"):
                self.clear_header(name)
            self.set_status(message["status"])
            for name, value in message.get("headers", []):
                self.add_header(name.decode("latin-1"), value.decode("latin-1"))
        elif message["type"] == "http.response.body":
            self.write(message.get("body", b""))
            if message.get("more_body", False):
                await self.flush()  # Backpressure: waits for the socket.
            elif not self.response_done.done():
                self.response_done.set_result(None)


class AsgiWebSocketHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, app, root_path):
        self.app = app
        self.root_path = root_path
        self.subprotocol = None

    def check_origin(self, origin):
        return True  # The ASGI app decides, for example with Mopidy middleware.

    def select_subprotocol(self, subprotocols):
        return self.subprotocol

    async def get(self, *args, **kwargs):
        self.receive_queue = asyncio.Queue()
        self.first_send = asyncio.get_running_loop().create_future()
        self.opened = asyncio.get_running_loop().create_future()
        offered = self.request.headers.get("Sec-WebSocket-Protocol", "")
        scope = make_scope(self, "websocket", self.root_path)
        scope["subprotocols"] = [p.strip() for p in offered.split(",") if p.strip()]
        self.receive_queue.put_nowait({"type": "websocket.connect"})
        self.app_task = asyncio.ensure_future(self.run_app(scope))

        first = await self.first_send
        if first["type"] != "websocket.accept":
            self.set_status(403)
            self.finish()
            return
        self.subprotocol = first.get("subprotocol")
        for name, value in first.get("headers", []):
            self.set_header(name.decode("latin-1"), value.decode("latin-1"))
        await super().get(*args, **kwargs)  # Handshake, then read frames.

    async def run_app(self, scope):
        try:
            await self.app(scope, self.receive, self.send)
        except Exception as exc:
            if not self.first_send.done():
                self.first_send.set_exception(exc)
                return
            traceback.print_exc()
        if not self.first_send.done():
            self.first_send.set_result({"type": "websocket.close"})
        elif self.ws_connection and not self.ws_connection.is_closing():
            self.close(1000)

    def open(self, *_args):
        self.opened.set_result(None)

    def on_message(self, message):
        key = "text" if isinstance(message, str) else "bytes"
        self.receive_queue.put_nowait({"type": "websocket.receive", key: message})

    def on_close(self):
        self.receive_queue.put_nowait(
            {
                "type": "websocket.disconnect",
                "code": self.close_code or 1005,
                "reason": self.close_reason or "",
            }
        )

    async def receive(self):
        return await self.receive_queue.get()

    async def send(self, message):
        if message["type"] in ("websocket.accept", "websocket.close"):
            if not self.first_send.done():
                self.first_send.set_result(message)
                return
        # Tornado ignores frames until its handshake is done.
        await self.opened
        if message["type"] == "websocket.close":
            self.close(message.get("code", 1000), message.get("reason") or None)
        elif message["type"] == "websocket.send":
            if message.get("text") is not None:
                await self.write_message(message["text"])  # Backpressure.
            else:
                await self.write_message(message["bytes"], binary=True)


class AsgiMatcher(tornado.routing.Matcher):
    def __init__(self, prefix, *, websocket):
        self.prefix = prefix
        self.websocket = websocket

    def match(self, request):
        path = request.path or ""
        if path != self.prefix and not path.startswith(self.prefix + "/"):
            return None
        is_websocket = request.headers.get("Upgrade", "").lower() == "websocket"
        return {} if is_websocket == self.websocket else None


def asgi_rules(prefix, app):
    kwargs = {"app": app, "root_path": prefix}
    return [
        tornado.routing.Rule(
            AsgiMatcher(prefix, websocket=True), AsgiWebSocketHandler, kwargs
        ),
        tornado.routing.Rule(
            AsgiMatcher(prefix, websocket=False), AsgiHttpHandler, kwargs
        ),
    ]


class Lifespan:
    def __init__(self, app):
        self.app = app
        self.receive_queue = asyncio.Queue()
        self.replies = asyncio.Queue()

    async def startup(self):
        scope = {"type": "lifespan", "asgi": ASGI, "state": {}}
        self.task = asyncio.ensure_future(
            self.app(scope, self.receive_queue.get, self.replies.put)
        )
        self.receive_queue.put_nowait({"type": "lifespan.startup"})
        return (await self.replies.get())["type"]

    async def shutdown(self):
        self.receive_queue.put_nowait({"type": "lifespan.shutdown"})
        reply = (await self.replies.get())["type"]
        await self.task
        return reply


# ---------------------------------------------------------------------------
# The ASGI app under test, as an extension would write it
# ---------------------------------------------------------------------------

observed: list[str] = []
flood = {"sent": 0}
endless = {"sent": 0}


@contextlib.asynccontextmanager
async def lifespan(_app):
    observed.append("app: lifespan startup")
    yield
    observed.append("app: lifespan shutdown")


async def hello(request):
    return JSONResponse(
        {
            "path": request.url.path,
            "root_path": request.scope["root_path"],
            "url_for": str(request.url_for("hello")),
            "query": request.query_params.get("q"),
        }
    )


async def item(request):
    return JSONResponse({"name": request.path_params["name"]})


async def upload(request):
    size = 0
    chunks = 0
    async for chunk in request.stream():
        size += len(chunk)
        chunks += 1
    return JSONResponse({"size": size, "chunks": chunks})


async def stream(_request):
    async def body():
        for i in range(3):
            yield f"chunk {i}\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(body(), media_type="text/plain", headers={"x-app": "1"})


async def forever(_request):
    async def body():
        while True:
            yield b"x" * 1024
            endless["sent"] += 1
            await asyncio.sleep(0.01)

    return StreamingResponse(body())


async def ws_echo(websocket):
    offered = websocket.scope["subprotocols"]
    await websocket.accept(
        subprotocol="b" if "b" in offered else None,
        headers=[(b"x-accepted", b"yes")],
    )
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            observed.append(f"app: disconnect code={message['code']}")
            return
        if message.get("text") is not None:
            await websocket.send_text("echo:" + message["text"])
        else:
            await websocket.send_bytes(b"echo:" + message["bytes"])


async def ws_reject(websocket):
    await websocket.close(code=1008)


async def ws_close(websocket):
    await websocket.accept()
    await websocket.close(code=4001, reason="bye")


async def ws_flood(websocket):
    await websocket.accept()
    for _ in range(200):
        await websocket.send_bytes(b"x" * (1 << 20))
        flood["sent"] += 1
    await websocket.close()


asgi_app = Starlette(
    routes=[
        Route("/hello", hello, name="hello"),
        Route("/items/{name}", item),
        Route("/upload", upload, methods=["POST"]),
        Route("/stream", stream),
        Route("/forever", forever),
        WebSocketRoute("/ws/echo", ws_echo),
        WebSocketRoute("/ws/reject", ws_reject),
        WebSocketRoute("/ws/close", ws_close),
        WebSocketRoute("/ws/flood", ws_flood),
    ],
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# A Tornado app, as extensions write them today
# ---------------------------------------------------------------------------


class LegacyHello(tornado.web.RequestHandler):
    def get(self):
        self.write("legacy hello")


class LegacyEcho(tornado.websocket.WebSocketHandler):
    def on_message(self, message):
        self.write_message("legacy:" + message)


# ---------------------------------------------------------------------------
# Server thread, like mopidy.http.actor.HttpServer
# ---------------------------------------------------------------------------


class Server(threading.Thread):
    def __init__(self):
        super().__init__(name="HttpServer", daemon=True)
        self.sockets = tornado.netutil.bind_sockets(0, "127.0.0.1")
        self.port = self.sockets[0].getsockname()[1]
        self.ready = threading.Event()

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        self.loop = asyncio.get_running_loop()
        self.stopping = asyncio.Event()
        lifespan_ = Lifespan(asgi_app)
        observed.append(f"bridge: lifespan startup -> {await lifespan_.startup()}")
        app = tornado.web.Application(
            [
                (r"/legacy/hello", LegacyHello),
                (r"/legacy/ws", LegacyEcho),
                *asgi_rules("/asgi", asgi_app),
            ]
        )
        server = tornado.httpserver.HTTPServer(app)
        server.add_sockets(self.sockets)
        self.ready.set()
        await self.stopping.wait()
        server.stop()
        observed.append(f"bridge: lifespan shutdown -> {await lifespan_.shutdown()}")

    def stop(self):
        self.loop.call_soon_threadsafe(self.stopping.set)
        self.join(timeout=5)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

results: list[tuple[bool, str, str]] = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, str(detail)))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def run_checks(port):
    base = f"http://127.0.0.1:{port}"
    ws_base = f"ws://127.0.0.1:{port}"
    http = httpx.Client(base_url=base, timeout=5)

    r = http.get("/legacy/hello")
    check("Tornado app HTTP still works", r.text == "legacy hello", r.text)

    r = http.get("/asgi/hello?q=1")
    body = r.json()
    check(
        "ASGI routing with root_path and url_for",
        body["path"] == "/asgi/hello"
        and body["url_for"].endswith("/asgi/hello")
        and body["query"] == "1",
        body,
    )
    check(
        "no Tornado default headers or ETag added",
        "server" not in r.headers
        and "etag" not in r.headers
        and r.headers["content-type"] == "application/json",
        dict(r.headers),
    )

    r = http.get("/asgi/items/a%20b")
    check("percent-decoded path params", r.json() == {"name": "a b"}, r.text)

    r = http.get("/asgi/missing")
    check("404 comes from the ASGI app", r.status_code == 404, r.status_code)

    r = http.post("/asgi/upload", content=b"x" * 5_000_000)
    check("5 MB request body", r.json()["size"] == 5_000_000, r.json())

    r = http.post("/asgi/upload", content=(b"y" * 65536 for _ in range(32)))
    check(
        "chunked request body streams in parts",
        r.json()["size"] == 32 * 65536 and r.json()["chunks"] > 1,
        r.json(),
    )

    chunks = []
    with http.stream("GET", "/asgi/stream") as r:
        for text in r.iter_text():
            chunks.append((round(time.monotonic(), 2), text))
        headers = dict(r.headers)
    check(
        "streamed response arrives in parts",
        len(chunks) >= 2 and headers.get("x-app") == "1",
        f"{len(chunks)} reads, transfer-encoding={headers.get('transfer-encoding')}",
    )

    with http.stream("GET", "/asgi/forever") as r:
        for i, _ in enumerate(r.iter_bytes()):
            if i >= 3:
                break
    time.sleep(0.3)
    before = endless["sent"]
    time.sleep(0.5)
    after = endless["sent"]
    check(
        "client disconnect stops a streamed response",
        before == after,
        f"chunks sent 0.3 s after close={before}, 0.8 s after close={after}",
    )

    asyncio.run(run_ws_checks(ws_base))


async def run_ws_checks(ws_base):
    connect = websockets.asyncio.client.connect

    async with connect(f"{ws_base}/legacy/ws") as ws:
        await ws.send("hi")
        check("Tornado app WebSocket still works", await ws.recv() == "legacy:hi")

    async with connect(f"{ws_base}/asgi/ws/echo", subprotocols=["a", "b"]) as ws:
        check(
            "subprotocol and accept headers",
            ws.subprotocol == "b" and ws.response.headers.get("x-accepted") == "yes",
            f"subprotocol={ws.subprotocol}",
        )
        await ws.send("hi")
        text = await ws.recv()
        await ws.send(b"hi")
        data = await ws.recv()
        check("text and binary echo", text == "echo:hi" and data == b"echo:hi")
        await ws.close(code=4002, reason="client bye")
    await asyncio.sleep(0.3)
    check(
        "app sees the client close code",
        "app: disconnect code=4002" in observed,
        observed,
    )

    try:
        async with connect(f"{ws_base}/asgi/ws/reject"):
            check("app can reject before the handshake", False, "connected")
    except websockets.exceptions.InvalidStatus as exc:
        status = exc.response.status_code
        check("app can reject before the handshake", status == 403, status)

    async with connect(f"{ws_base}/asgi/ws/close") as ws:
        try:
            await ws.recv()
        except websockets.exceptions.ConnectionClosed as exc:
            rcvd = exc.rcvd
            check(
                "app close code and reason reach the client",
                rcvd and rcvd.code == 4001 and rcvd.reason == "bye",
                rcvd,
            )

    async with connect(f"{ws_base}/asgi/ws/flood", max_size=None, max_queue=1) as ws:
        await asyncio.sleep(1)  # Do not read.
        sent_while_paused = flood["sent"]
        received = 0
        with contextlib.suppress(websockets.exceptions.ConnectionClosed):
            while True:
                await ws.recv()
                received += 1
    check(
        "send() blocks while the client does not read (200 x 1 MB)",
        sent_while_paused < 50 and received == 200,
        f"sent while paused={sent_while_paused}, received={received}",
    )


def main():
    server = Server()
    server.start()
    server.ready.wait(5)
    try:
        run_checks(server.port)
    finally:
        server.stop()
    check(
        "lifespan startup and shutdown",
        "bridge: lifespan startup -> lifespan.startup.complete" in observed
        and "bridge: lifespan shutdown -> lifespan.shutdown.complete" in observed,
        [o for o in observed if "lifespan" in o],
    )
    failed = [name for ok, name, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")


if __name__ == "__main__":
    main()
