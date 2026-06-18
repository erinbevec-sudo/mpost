from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"  # development or production
    database_url: str = "postgresql+psycopg://mpost:mpost@localhost:5432/mpost"
    embedding_model: str = "mpost-hash-384"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    llm_provider: str = "huggingface"
    # Hugging Face settings
    hf_model: str = "meta-llama/Llama-3.2-3B-Instruct"
    hf_api_token: str = ""
    # Ollama settings (local alternative)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    mpost_dev_user_email: str = "user@example.com"
    mpost_dev_user_role: str = "user"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
