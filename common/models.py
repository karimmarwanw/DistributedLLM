from pydantic import BaseModel


class RequestModel(BaseModel):
    id: int
    query: str
    max_tokens: int | None = None


class ResponseModel(BaseModel):
    id: int
    result: str
    worker_id: int
    master_id: int
    latency: float
    gpu_utilization_percent: float | None = None
    master_gpu_utilization_percent: float | None = None
    worker_gpu_utilization_percent: float | None = None
    gpu_utilization_source: str | None = None
    gpu_capacity: int | None = None
    gpu_model: str | None = None
    gpu_core_count: int | None = None
    llm_model: str | None = None
    success: bool
