"""
Local capture server for reverse-engineering the FGG web app's WebHID writes.

The in-page logger (pasted into the vendor web app's DevTools console) POSTs each
sendReport/sendFeatureReport call here; we append it to a log file so the captured
reports can be reviewed without manual copy-paste. Browsers permit a page (even HTTPS) to
reach http://127.0.0.1, so no CORS/mixed-content workaround is needed beyond the
permissive headers below. Pure stdlib, no third-party packages.

Run:  python tools/webhid_beacon.py
Log:  tools/webhid_capture.log   (appended; one report per line, timestamped)
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import datetime

LOG = Path(__file__).with_name("webhid_capture.log")


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n).decode("utf-8", "replace")
        line = f'{datetime.datetime.now():%H:%M:%S}  {body}'
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line, flush=True)
        self.send_response(200)
        self._cors()
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    LOG.write_text("", encoding="utf-8")   # fresh log each run
    print(f"webhid beacon listening on http://127.0.0.1:8765  ->  {LOG}", flush=True)
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
