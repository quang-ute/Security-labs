"""
mitmproxy addon for WSS — Web Security School.

Annotates flows with vulnerability tags and logs suspicious patterns so
students can see exactly what the exploit looks like on the wire.

Usage:  mitmweb -s mitm_addon.py
        mitmproxy -s mitm_addon.py
"""
import re
import sys
import urllib.parse

from mitmproxy import http, ctx

# Windows consoles/redirects may use cp1252, which cannot encode the emoji in the
# log messages below — mitmproxy's termlog would then raise during emit and the
# flow itself goes stale. Force UTF-8 on the standard streams.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — never break the proxy over logging
            pass


class WSSLabAddon:
    """Highlight vulnerability-relevant HTTP traffic."""

    # The app is reachable as 15000 directly, or as 18080 when mitmproxy runs
    # in reverse mode (``--mode reverse:http://127.0.0.1:15000@18080``).
    APP_BASE = "http://127.0.0.1:15000"
    APP_BASES = (APP_BASE, "http://127.0.0.1:18080", "http://localhost:18080")

    @classmethod
    def _is_app(cls, url: str) -> bool:
        return url.startswith(cls.APP_BASES)

    def request(self, flow: http.HTTPFlow) -> None:
        """Inspect outgoing requests and tag them."""
        self._tag_csrf(flow)
        self._tag_sqli(flow)
        self._tag_ssti(flow)
        self._tag_command_injection(flow)
        self._tag_ssrf(flow)
        self._tag_path_traversal(flow)
        self._tag_idor(flow)
        self._tag_xss_request(flow)
        self._tag_open_redirect_req(flow)

    def response(self, flow: http.HTTPFlow) -> None:
        """Inspect incoming responses."""
        self._tag_xss_response(flow)
        self._tag_open_redirect_resp(flow)
        self._check_security_headers(flow)
        self._tag_ssti_response(flow)

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------
    def _t(self, flow: http.HTTPFlow, tag: str) -> None:
        if tag not in flow.metadata:
            flow.metadata[tag] = True
            ctx.log.info(f"[WSS] ⚠ {tag}")
            # Also add a comment visible in the flow list
            if tag not in (flow.comment or ""):
                flow.comment = (flow.comment or "") + f" [{tag}]"

    # ------------------------------------------------------------------
    # CSRF — POST to /profile should have a token
    # ------------------------------------------------------------------
    def _tag_csrf(self, flow: http.HTTPFlow) -> None:
        if self._is_app(flow.request.pretty_url):
            if flow.request.method == "POST" and "/profile" in flow.request.path:
                body = flow.request.get_text() or ""
                if "csrf_token" not in body:
                    self._t(flow, "CSRF (no anti-CSRF token)")

    # ------------------------------------------------------------------
    # SQLi — look for SQL metacharacters in login POST
    # ------------------------------------------------------------------
    SQLI_PATTERNS = [
        r"(--|\#)",           # comment injection
        r"'?\s*OR\s+'?1\s*=\s*1",  # tautology
        r"UNION\s+SELECT",
        r"'\s*;",
    ]

    def _tag_sqli(self, flow: http.HTTPFlow) -> None:
        if flow.request.method == "POST" and "/login" in flow.request.path:
            body = flow.request.get_text() or ""
            for pat in self.SQLI_PATTERNS:
                if re.search(pat, body, re.IGNORECASE):
                    self._t(flow, f"SQLi (matched: {pat})")
                    break

    # ------------------------------------------------------------------
    # SSTI — Jinja2 template syntax in URL or body
    # ------------------------------------------------------------------
    SSTI_PATTERN = r"\{\{.*\}\}"

    def _tag_ssti(self, flow: http.HTTPFlow) -> None:
        if "/greet" in flow.request.path:
            raw = flow.request.pretty_url + " " + (flow.request.get_text() or "")
            if re.search(self.SSTI_PATTERN, urllib.parse.unquote(raw)):
                self._t(flow, "SSTI (template injection in URL)")

    def _tag_ssti_response(self, flow: http.HTTPFlow) -> None:
        """If request was SSTI, confirm evaluation in response."""
        if flow.metadata.get("SSTI"):
            resp = flow.response
            if resp and "Hello, " in (resp.get_text() or ""):
                ctx.log.info("[WSS] ✅ SSTI confirmed — expression evaluated")

    # ------------------------------------------------------------------
    # Command Injection — shell metacharacters in ping body
    # ------------------------------------------------------------------
    CMD_INJECT_PATTERNS = [r"[;|&$`]", r"\$\(.*\)", r"`.*`"]

    def _tag_command_injection(self, flow: http.HTTPFlow) -> None:
        if flow.request.method == "POST" and "/ping" in flow.request.path:
            body = flow.request.get_text() or ""
            for pat in self.CMD_INJECT_PATTERNS:
                if re.search(pat, body):
                    self._t(flow, f"Command Injection (matched: {pat})")
                    break

    # ------------------------------------------------------------------
    # SSRF — server-side request to internal address
    # ------------------------------------------------------------------
    def _tag_ssrf(self, flow: http.HTTPFlow) -> None:
        if flow.request.method == "POST" and "/ssrf" in flow.request.path:
            body = flow.request.get_text() or ""
            if any(kw in body for kw in ("file://", "127.0.0.1", "localhost",
                                          "169.254", "10.", "192.168.", "172.")):
                self._t(flow, "SSRF (internal/private target)")

    # ------------------------------------------------------------------
    # Path Traversal — URL-encoded ../ in path
    # ------------------------------------------------------------------
    def _tag_path_traversal(self, flow: http.HTTPFlow) -> None:
        if "/files/" in flow.request.path or "/notes/attachment/" in flow.request.path:
            if "%2e" in flow.request.path or ".." in flow.request.path:
                self._t(flow, "Path Traversal (directory escape)")

    # ------------------------------------------------------------------
    # IDOR — access note belonging to another user
    # ------------------------------------------------------------------
    def _tag_idor(self, flow: http.HTTPFlow) -> None:
        m = re.match(r".*/notes/(\d+)$", flow.request.path)
        if m:
            note_id = int(m.group(1))
            # Notes 3-5 belong to users other than the first demo user
            if note_id in (3, 4, 5):
                self._t(flow, f"IDOR (note #{note_id} may belong to another user)")

    # ------------------------------------------------------------------
    # XSS — injected <script> in request (reflected) or response
    # ------------------------------------------------------------------
    XSS_REQ_PATTERN = r"<script[^>]*>.*</script>"

    def _tag_xss_request(self, flow: http.HTTPFlow) -> None:
        if "/search" in flow.request.path:
            q = flow.request.query.get("q", "")
            if re.search(self.XSS_REQ_PATTERN, q, re.IGNORECASE):
                self._t(flow, "XSS (reflected — script injected in query)")

    def _tag_xss_response(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if not resp:
            return
        body = resp.get_text() or ""
        # Check if response contains unescaped script tags
        if re.search(self.XSS_REQ_PATTERN, body, re.IGNORECASE):
            # Avoid double-tagging (already tagged in request)
            if not any("XSS" in (flow.comment or "").split() for t in [""]):
                self._t(flow, "XSS (raw script in response)")

    # ------------------------------------------------------------------
    # Open Redirect — 302 Location to external host
    # ------------------------------------------------------------------
    def _tag_open_redirect_req(self, flow: http.HTTPFlow) -> None:
        if "/logout" in flow.request.path or "/proxy" in flow.request.path:
            url = flow.request.pretty_url
            if "next=" in url or "to=" in url:
                self._t(flow, "Open Redirect (user-controlled redirect)")

    def _tag_open_redirect_resp(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if not resp:
            return
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location", "")
            # Relative targets ("", "/dashboard") are normal app redirects; only
            # absolute URLs pointing off-host are interesting.
            is_absolute = location.startswith(("http://", "https://", "//"))
            if is_absolute and not self._is_app(location):
                self._t(flow, f"Open Redirect → {location}")

    # ------------------------------------------------------------------
    # Security headers audit
    # ------------------------------------------------------------------
    def _check_security_headers(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        if not resp:
            return
        headers = resp.headers
        issues = []

        # Content-Security-Policy
        if "Content-Security-Policy" not in headers:
            issues.append("No CSP header")

        # X-Content-Type-Options
        if "X-Content-Type-Options" not in headers:
            issues.append("No X-Content-Type-Options")

        # X-Frame-Options
        if "X-Frame-Options" not in headers:
            issues.append("No X-Frame-Options")

        # Set-Cookie (session cookie)
        set_cookie = headers.get("Set-Cookie", "")
        if set_cookie and "HttpOnly" not in set_cookie:
            issues.append("Session cookie missing HttpOnly")
        if set_cookie and "SameSite" not in set_cookie:
            issues.append("Session cookie missing SameSite")

        if issues:
            for issue in issues:
                ctx.log.info(f"[WSS] 🛡 Missing: {issue}")


addons = [WSSLabAddon()]