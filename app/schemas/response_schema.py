from pydantic import BaseModel
from typing import Any

class ClaimResponse(BaseModel):
    result: Any

class RiskResponse(BaseModel):
    result: Any

class ChatResponse(BaseModel):
    result: str

class WhatIfResponse(BaseModel):
    result: Any
