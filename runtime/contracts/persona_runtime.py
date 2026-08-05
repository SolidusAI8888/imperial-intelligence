from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RuntimeMode(str, Enum):
    """人格运行模式。"""

    CONSULTATION = "consultation"
    ROUNDTABLE = "roundtable"
    SIMULATION = "simulation"


class EvidencePolicy(str, Enum):
    """回答所采用的史料证据标准。"""

    STRICT = "strict"
    BALANCED = "balanced"
    EXPLORATORY = "exploratory"


class HistoricalKnowledgeBoundary(BaseModel):
    """规定历史人格在当前阶段可以知道哪些信息。"""

    model_config = ConfigDict(extra="forbid")

    cutoff_date: str = Field(
        ...,
        description="人格所处的历史时间点，例如 641-12-31",
    )

    allow_posthumous_knowledge: bool = Field(
        default=False,
        description="是否允许知道该历史时间点之后发生的事情",
    )

    allow_modern_context: bool = Field(
        default=True,
        description="是否允许系统理解用户的现代社会背景",
    )

    allow_modern_terms: bool = Field(
        default=True,
        description="是否允许把现代概念转换为历史人物可理解的等价概念",
    )


class PersonaRuntimeContext(BaseModel):
    """单次历史人格运行实例的完整上下文。"""

    model_config = ConfigDict(extra="forbid")

    runtime_id: UUID = Field(
        default_factory=uuid4,
        description="本次人格运行实例的唯一标识",
    )

    emperor_id: str = Field(
        ...,
        min_length=1,
        description="帝王唯一标识，例如 tang_taizong",
    )

    persona_package_version: str = Field(
        default="0.1.0",
        description="当前人格数据包版本",
    )

    historical_stage_id: str = Field(
        ...,
        min_length=1,
        description="人生阶段标识，例如 zhenguan_15",
    )

    historical_stage_name: str = Field(
        ...,
        min_length=1,
        description="人生阶段名称，例如 贞观十五年",
    )

    runtime_mode: RuntimeMode = Field(
        default=RuntimeMode.CONSULTATION,
    )

    evidence_policy: EvidencePolicy = Field(
        default=EvidencePolicy.BALANCED,
    )

    knowledge_boundary: HistoricalKnowledgeBoundary

    active_traits: list[str] = Field(default_factory=list)

    active_memories: list[str] = Field(default_factory=list)

    active_relationships: list[str] = Field(default_factory=list)

    emotional_state: dict[str, float] = Field(default_factory=dict)

    runtime_variables: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )