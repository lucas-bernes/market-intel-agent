from pydantic import BaseModel
from typing import Optional

class ModelComparison(BaseModel):
    model_name: str
    provider: str
    price_per_second_usd: float
    max_reference_images: int
    prompt_window_tokens: int
    multi_shot_support: bool
    notes: Optional[str] = None