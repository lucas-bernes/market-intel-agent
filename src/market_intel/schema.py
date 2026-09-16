from pydantic import BaseModel, Field
from typing import Optional

class ModelComparison(BaseModel):
    model_name: str
    provider: str
    price_per_second_usd: Optional[float] = None
    max_reference_images: Optional[int] = None
    prompt_window_tokens: Optional[int] = None
    multi_shot_support: Optional[bool] = None
    quality_notes: Optional[str] = Field(
        default=None,
        description=(
            "Summary of what reviews/benchmarks say about output quality: "
            "realism, visual consistency across frames, and known "
            "hallucination/artifact issues (e.g. distorted hands, drift)."
        ),
    )
    notes: Optional[str] = None