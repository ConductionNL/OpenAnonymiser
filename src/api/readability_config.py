import os
from dataclasses import dataclass
from typing import Optional, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class LimitsModel(BaseModel):
    max_text_length: int = 200_000


class LixBandsModel(BaseModel):
    easy: float = 30.0
    medium: float = 40.0
    complex: float = 55.0


class LixModel(BaseModel):
    long_word_min_len: int = 7  # >6 letters by default
    judgement_bands: LixBandsModel = Field(default_factory=LixBandsModel)

    @field_validator("long_word_min_len")
    @classmethod
    def _min_len_guard(cls, v: int) -> int:
        if v < 2:
            raise ValueError("long_word_min_len must be >= 2")
        return v


class FleschDoumaModel(BaseModel):
    enabled_by_default: bool = False
    syllables_per_word_min: float = 0.8
    syllables_per_word_max: float = 4.0
    invalid_policy: Literal["null", "status_object"] = "null"


class OutputModel(BaseModel):
    include_debug_fields: bool = True
    include_cefr_hint: bool = True
    cefr_confidence_cap: float = 0.4


class ReadabilityConfigModel(BaseModel):
    version: int = 1
    limits: LimitsModel = Field(default_factory=LimitsModel)
    lix: LixModel = Field(default_factory=LixModel)
    flesch_douma: FleschDoumaModel = Field(default_factory=FleschDoumaModel)
    output: OutputModel = Field(default_factory=OutputModel)


READABILITY_CONFIG: Optional[ReadabilityConfigModel] = None


def _config_path_from_env() -> str:
    profile = os.getenv("READABILITY_PROFILE", "local").lower()
    if profile not in ("local", "online"):
        profile = "local"
    return os.path.join("config", f"readability.{profile}.yaml")


def load_readability_config() -> ReadabilityConfigModel:
    path = _config_path_from_env()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Readability config not found at '{path}'. "
            "Set READABILITY_PROFILE=local|online and ensure the file exists."
        )
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    try:
        cfg = ReadabilityConfigModel.model_validate(raw)
    except ValidationError as ve:
        raise ValueError(f"Invalid readability config at '{path}': {ve}") from ve
    return cfg


def get_readability_config() -> ReadabilityConfigModel:
    global READABILITY_CONFIG
    if READABILITY_CONFIG is None:
        READABILITY_CONFIG = load_readability_config()
    return READABILITY_CONFIG


