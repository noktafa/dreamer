from pydantic import BaseModel


class OrderRequest(BaseModel):
    customer_id: str
    amount: float
    currency: str = "TRY"


class OrderResponse(BaseModel):
    correlation_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    server: str
    timestamp: str
