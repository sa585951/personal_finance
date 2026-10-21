from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class SecuritySettings:
    environment: str
    frontend_origin: str
    login_origin: str
    dev_auth_bypass: bool

    @property
    def secure_cookies(self):
        return self.environment == "production"


def _origin(value):
    parsed = urlsplit(value or "")
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("公開網址必須是完整的 HTTP(S) origin，不可包含路徑或憑證")
    return parsed, f"{parsed.scheme}://{parsed.netloc}"


def load_security_settings(environ):
    # Missing/unknown environment must never implicitly enable development auth.
    environment = environ.get("NOMICA_ENV") or environ.get("FLASK_ENV") or "production"
    if environment not in {"production", "development", "testing"}:
        raise ValueError("NOMICA_ENV / FLASK_ENV 必須明確為 production、development 或 testing")
    frontend, frontend_origin = _origin(environ.get("FRONTEND_BASE_URL"))
    login, login_origin = _origin(environ.get("VITE_BACKEND_BASE_URL"))
    bypass = environ.get("DEV_AUTH_BYPASS", "false").lower()
    if bypass not in {"true", "false"}:
        raise ValueError("DEV_AUTH_BYPASS 必須為 true 或 false")
    if environment == "production":
        if bypass == "true" or environ.get("FLASK_DEBUG", "").lower() not in {"", "0", "false", "no"}:
            raise ValueError("正式環境禁止 dev auth bypass 或 debug")
        if frontend.scheme != "https" or login.scheme != "https" or frontend_origin != login_origin:
            raise ValueError("正式 Web 登入須透過同一 HTTPS origin 代理 API 與 LINE callback")
    elif any(url.hostname not in {"localhost", "127.0.0.1", "::1"} for url in (frontend, login)):
        raise ValueError("development / testing 僅允許 loopback origin；公開網址須使用 production")
    return SecuritySettings(environment, frontend_origin, login_origin, bypass == "true")
