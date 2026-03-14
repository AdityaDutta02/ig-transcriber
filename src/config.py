"""
Configuration Management Module

Handles loading and validation of configuration from YAML files and environment variables.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, validator
from pydantic_settings import BaseSettings


class InputConfig(BaseModel):
    """Input configuration."""
    csv_path: str
    url_column: str = "url"
    skip_processed: bool = True
    validate_urls: bool = True


class DownloadConfig(BaseModel):
    """Download configuration."""
    concurrent_workers: int = Field(12, ge=1, le=50)
    timeout: int = Field(30, ge=5)
    retry_attempts: int = Field(3, ge=0)
    retry_delay: int = Field(2, ge=0)
    rate_limit_delay: float = Field(0.5, ge=0)
    user_agent: str
    format: str = "bestaudio"
    extract_audio: bool = True
    audio_format: str = "wav"
    audio_quality: str = "0"


class TranscriptionConfig(BaseModel):
    """
    Transcription configuration for the Groq Whisper Large v3 API.

    Unknown fields from older config files (e.g. model, device, compute_type)
    are silently ignored via ConfigDict(extra='ignore').
    """

    model_config = ConfigDict(extra="ignore")

    api_provider: str = "groq"
    language: str = "auto"


class CaptionConfig(BaseModel):
    """Caption configuration."""
    enabled: bool = True
    words_per_line: int = Field(10, ge=1, le=20)
    max_lines: int = Field(2, ge=1, le=3)
    format: str = Field("srt", pattern="^(srt|vtt)$")


class OutputConfig(BaseModel):
    """Output configuration."""
    directory: str
    format: str = "txt"
    encoding: str = "utf-8"
    naming_pattern: str = "{timestamp}_{id}"
    include_metadata: bool = True
    metadata: List[str] = Field(
        default=["url", "timestamp", "duration", "language", "api_provider", "processing_time"]
    )


class ProcessingConfig(BaseModel):
    """Processing configuration."""
    batch_size: int = Field(100, ge=1)
    temp_directory: str
    cleanup_temp: bool = True
    save_checkpoint: bool = True
    checkpoint_interval: int = Field(10, ge=1)
    checkpoint_file: str


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    console: bool = True
    file: str
    max_file_size: str = "10MB"
    backup_count: int = Field(5, ge=0)
    format: str
    error_file: str


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    enabled: bool = True
    track_metrics: bool = True
    report_interval: int = Field(30, ge=1)
    save_report: bool = True
    report_path: str


class ErrorHandlingConfig(BaseModel):
    """Error handling configuration."""
    continue_on_error: bool = True
    max_consecutive_errors: int = Field(5, ge=1)
    save_failed_urls: bool = True
    failed_urls_path: str
    exponential_backoff: bool = True
    max_backoff_time: int = Field(60, ge=1)


class AppConfig(BaseModel):
    """Main application configuration."""
    input: InputConfig
    download: DownloadConfig
    transcription: TranscriptionConfig
    captions: CaptionConfig
    output: OutputConfig
    processing: ProcessingConfig
    logging: LoggingConfig
    monitoring: MonitoringConfig
    error_handling: ErrorHandlingConfig


def load_config(config_path: str = "config/config.yaml") -> AppConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration YAML file

    Returns:
        AppConfig object with validated configuration

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, "r") as f:
        config_dict = yaml.safe_load(f)

    return AppConfig(**config_dict)


def save_config(config: AppConfig, config_path: str = "config/config.yaml") -> None:
    """
    Save configuration to YAML file.

    Args:
        config: AppConfig object
        config_path: Path to save configuration
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    config = load_config()
    print("Configuration loaded successfully!")
    print(f"API provider: {config.transcription.api_provider}")
    print(f"Language: {config.transcription.language}")
    print(f"Download workers: {config.download.concurrent_workers}")
