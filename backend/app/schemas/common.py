from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseSchema):
    error: str
    detail: str | None = None
    code: str | None = None


class SuccessResponse(BaseSchema):
    message: str
    data: dict | None = None
