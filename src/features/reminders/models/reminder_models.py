"""
Database models for the reminder system.
Defines the schema for reminder templates, reminders, and logs.
"""

from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, BigInteger
from sqlalchemy.orm import relationship

# Import reminder models from main database models instead of redefining them
from src.database.models import Base, ReminderTemplate, Reminder, ReminderLog

# Feature-specific models can still be defined here if needed
# But core models should be imported from the main database models