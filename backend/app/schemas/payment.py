from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class PaymentMethodCreate(BaseModel):
    provider: str = Field(default="stripe", description="Payment provider identifier (e.g. stripe, paypal)")
    payment_token: str = Field(..., description="Secure payment method token/vault id from payment gateway")
    brand: str = Field(default="visa", description="Card brand (visa, mastercard, amex, etc.)")
    last4: str = Field(..., min_length=4, max_length=4, description="Last 4 digits of the card")
    exp_month: int = Field(..., ge=1, le=12, description="Expiration month (1-12)")
    exp_year: int = Field(..., ge=2024, le=2100, description="Expiration year (4 digits)")
    holder_name: Optional[str] = Field(None, description="Cardholder full name")
    is_default: bool = Field(default=False, description="Set as default payment method")


class PaymentMethodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    provider: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    holder_name: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class PaymentMethodListResponse(BaseModel):
    payment_methods: List[PaymentMethodRead]
    count: int


class SetDefaultPaymentMethodRequest(BaseModel):
    payment_method_id: str
