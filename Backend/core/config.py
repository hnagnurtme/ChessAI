from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Engine mặc định: "v1" | "v2" | "vip"
    default_engine: str = "vip"

    # Giới hạn thời gian suy nghĩ mặc định (giây)
    default_time_limit: float = 1.0

    # Độ sâu tìm kiếm mặc định
    default_depth: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
