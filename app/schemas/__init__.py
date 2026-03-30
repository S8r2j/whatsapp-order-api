"""Pydantic schema exports."""

from app.schemas.auth import LoginRequest, RegisterRequest, ShopResponse, TokenResponse
from app.schemas.common import ErrorResponse, HealthResponse, PaginatedResponse
from app.schemas.connection import ConnectMetaResponse, SocialConnectionResponse
from app.schemas.customer import CustomerResponse, UpdateCustomerRequest
from app.schemas.message import MessageResponse
from app.schemas.order import (
    OrderDetailResponse,
    OrderItemSchema,
    OrderResponse,
    ReplyToOrderRequest,
    UpdateOrderNotesRequest,
    UpdateOrderStatusRequest,
)
from app.schemas.shop import (
    ShopProfileResponse,
    UpdateBusinessHoursRequest,
    UpdateShopProfileRequest,
)

__all__ = [
    "LoginRequest", "RegisterRequest", "ShopResponse", "TokenResponse",
    "ErrorResponse", "HealthResponse", "PaginatedResponse",
    "CustomerResponse", "UpdateCustomerRequest",
    "MessageResponse",
    "OrderDetailResponse", "OrderItemSchema", "OrderResponse",
    "ReplyToOrderRequest", "UpdateOrderNotesRequest", "UpdateOrderStatusRequest",
    "ShopProfileResponse", "UpdateBusinessHoursRequest", "UpdateShopProfileRequest",
    "SocialConnectionResponse", "ConnectMetaResponse",
]
