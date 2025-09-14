"""Core/system schemas: system, embeddings, storage, emotion, reflection."""
from __future__ import annotations

from pydantic import BaseModel


class EmbeddingConfig(BaseModel):
    id: str


class EmbeddingsConfig(BaseModel):
    main: EmbeddingConfig = EmbeddingConfig(id="bge-m3")
    fallback: EmbeddingConfig = EmbeddingConfig(id="gte-small")


class EmotionFSMConfig(BaseModel):
    hysteresis_ms: int = 2000


class EmotionModelRef(BaseModel):
    id: str


class EmotionConfig(BaseModel):
    model: EmotionModelRef = EmotionModelRef(
        id="distilroberta-multilingual-emotion"
    )
    fsm: EmotionFSMConfig = EmotionFSMConfig()


class ReflectionSchedule(BaseModel):
    cron: str = "0 3 * * *"


class ReflectionConfig(BaseModel):
    enabled: bool = True
    schedule: ReflectionSchedule = ReflectionSchedule()


class StoragePathsConfig(BaseModel):
    models: str = "models"
    cache: str = ".cache"
    data: str = "data"


class StorageConfig(BaseModel):
    paths: StoragePathsConfig = StoragePathsConfig()


class SystemConfig(BaseModel):
    locale: str = "ru-RU"
    timezone: str = "Europe/Moscow"
