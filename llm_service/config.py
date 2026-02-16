from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ELASTICSEARCH_HOST: str = "localhost"
    ELASTICSEARCH_PORT: int = 9200
    ELASTICSEARCH_INDEX: str = "banking-poc-logs-*"

    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4o"

    LLM_LOG_PATH: str = "/var/log/llm_service/llm_service.log"
    MAX_LOG_ENTRIES: int = 50

    model_config = {"env_prefix": ""}


settings = Settings()
