"""Application settings management for the smart customer service system."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SMART_CS_", extra="ignore")

    app_name: str = Field(default="Smart Customer Service")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    timezone: str = Field(default="Asia/Shanghai")
    system_prompt: str = Field(
        default=(
            "你是一个专业而温暖的中文客服，会耐心地引导用户完成订单查询、退款和发票开具。"
        )
    )
    model_style: str = Field(default="balanced", description="响应语气，可选 warm/balanced/concise")
    llm_provider: str = Field(default="local", description="local 或 tongyi")
    llm_temperature: float = Field(default=0.2)
    dashscope_model: str = Field(default="qwen-plus")
    dashscope_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DASHSCOPE_API_KEY", "SMART_CS_DASHSCOPE_API_KEY"),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance to avoid repeated file reads."""

    return Settings()
