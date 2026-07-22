from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    obsidian_rest_api_key: str = ""
    obsidian_https_url: str = "https://127.0.0.1:27124"
    obsidian_http_url: str = "http://127.0.0.1:27123"
    obsidian_cert_path: str | None = None
    allow_http_fallback: bool = True
    dlp_hit_policy: str = "redact"  # redact | block | quarantine
    enable_secrets_rotation: bool = True
    enable_otel: bool = False

    context_server_host: str = "127.0.0.1"
    context_server_port: int = 27180
    hooks_dir: str = "../hooks"
    identity_secret: str = ""

    def validate_identity_secret(self) -> None:
        if not self.identity_secret or self.identity_secret in ("default-insecure-secret", "change-me"):
            raise RuntimeError(
                "FATAL: identity_secret is unset or uses a known-default value. "
                "Set IDENTITY_SECRET in .env to a strong random string (at least 32 chars). "
                "The server refuses to start with a forgeable identity secret."
            )


settings = Settings()
settings.validate_identity_secret()
