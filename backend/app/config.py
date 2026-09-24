from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/patient_reg"
    )

    # Retell API key. Used to verify inbound webhook signatures
    # (retell.Retell.verify) and, in tooling scripts, to call the Retell API.
    # Leave empty locally; set it as an env var on Railway.
    retell_api_key: str = ""

    # When false, the Retell webhook accepts unsigned requests. Keep true in
    # production; tests and local calls without a signature can set it to false.
    verify_retell_signature: bool = True


settings = Settings()
