import http.server
import functools

http.server.SimpleHTTPRequestHandler.extensions_map.update({
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
})


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()


handler = functools.partial(NoCacheHandler, directory=".")
http.server.test(HandlerClass=handler, port=8080, bind="0.0.0.0")
