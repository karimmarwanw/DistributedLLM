from pydantic import BaseModel


class RequestModel(BaseModel):
    id: int
    query: str


class ResponseModel(BaseModel):
    id: int
    result: str
    worker_id: int
    master_id: int
    latency: float
    success: bool