import http.server
import functools

http.server.SimpleHTTPRequestHandler.extensions_map.update({
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
})

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=".")
http.server.test(HandlerClass=handler, port=8080, bind="0.0.0.0")
