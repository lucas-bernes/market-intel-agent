from pydantic import BaseModel
from typing import Optional

class ModelComparison(BaseModel):
    model_name: str
    provider: str
    price_per_second_usd: Optional[float] = None
    max_reference_images: Optional[int] = None
    prompt_window_tokens: Optional[int] = None
    multi_shot_support: Optional[bool] = None
    notes: Optional[str] = None