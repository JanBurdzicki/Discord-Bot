"""
Database models for the user management system.
Defines the schema for user profiles and related data.
"""

from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship

# Import UserProfile from main database models instead of redefining it
from src.database.models import Base, UserProfile

class UserLog(Base):
    """
    Log entry for user-related operations.
    Tracks changes to user profiles and roles.
    """
    __tablename__ = "user_logs"

    id = Column(Integer, primary_key=True, index=True)
    discord_id = Column(BigInteger, ForeignKey("user_profiles.discord_id"), nullable=False)
    action = Column(String, nullable=False)  # created, updated, role_added, role_removed, etc.
    details = Column(JSON, default={})  # Additional action details
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Note: UserProfile relationship would need to be added to main models if needed