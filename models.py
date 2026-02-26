"""
Pydantic models used across the multi-agent system.
"""

from typing import List
from pydantic import BaseModel, Field


class UserInput(BaseModel):
    """Schema for parsing user-provided account information."""
    identifier: str = Field(
        default="",
        description="Identifier: can be a customer ID, email, or phone number."
    )


class UserProfile(BaseModel):
    """Schema for storing user music preferences in long-term memory."""
    customer_id: str = Field(description="The customer ID of the customer")
    music_preferences: List[str] = Field(
        default_factory=list,
        description="The music preferences of the customer"
    )
