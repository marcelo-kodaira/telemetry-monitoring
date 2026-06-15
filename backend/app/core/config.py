from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://fleet:fleet@localhost:5432/fleet"
    pool_min_size: int = 10
    pool_max_size: int = 20

    battery_low_pct: int = 15
    battery_critical_pct: int = 5
    overspeed_mps: float = 3.0          # policy / safety limit
    teleport_mps: float = 8.0           # physical-impossibility limit (~2x physical max)
    battery_drain_pct_per_s: float = 2.0
    staleness_seconds: int = 10
    sweep_interval_seconds: int = 5


settings = Settings()
