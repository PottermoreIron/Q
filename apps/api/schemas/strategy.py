from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StrategyBlockIn(BaseModel):
    id: str
    type: str  # indicator | condition | action | filter
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)


class StrategyIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    blocks: List[StrategyBlockIn] = Field(default_factory=list)
    python_code: Optional[str] = None


class StrategyPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    blocks: Optional[List[StrategyBlockIn]] = None
    python_code: Optional[str] = None


class StrategyOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    blocks: List[Dict[str, Any]]
    python_code: Optional[str]
    user_id: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ValidateCodeIn(BaseModel):
    code: str


class ValidateCodeOut(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)


class CompileBlocksOut(BaseModel):
    python_code: str
