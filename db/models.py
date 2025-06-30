from sqlalchemy import Column, Integer, BigInteger, String, Boolean, DateTime, ForeignKey, JSON, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    discord_id = Column(BigInteger, primary_key=True)
    calendar_email = Column(String)
    preferences = Column(JSON, default={})
    roles = Column(JSON, default=[])

class UserToken(Base):
    __tablename__ = 'user_tokens'
    discord_id = Column(BigInteger, ForeignKey('user_profiles.discord_id'), primary_key=True)
    token_data = Column(JSON)

class EventReservation(Base):
    __tablename__ = 'event_reservations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_title = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    organizer_id = Column(BigInteger)
    participant_ids = Column(JSON)
    calendar_event_ids = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CalendarEvent:
    def __init__(self, event_id: str, title: str, start_time, end_time):
        self.event_id = event_id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time

class Poll(Base):
    __tablename__ = 'polls'
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String, unique=True, nullable=False)
    question = Column(String, nullable=False)
    options = Column(String, nullable=False)  # Comma-separated options
    creator_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger)  # Channel where poll was created
    is_active = Column(Boolean, default=True)
    is_advanced = Column(Boolean, default=False)
    external_id = Column(String)  # For advanced polls (e.g., StrawPoll ID)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(String, ForeignKey('polls.poll_id'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    option_index = Column(Integer, nullable=False)
    voted_at = Column(DateTime, default=datetime.utcnow)

class SharedCalendar(Base):
    __tablename__ = "shared_calendars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    google_calendar_id = Column(String, nullable=True)  # Google Calendar ID
    created_by = Column(BigInteger, nullable=False)  # Discord user ID of creator
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    permissions = relationship("CalendarPermission", back_populates="calendar", cascade="all, delete-orphan")
    events = relationship("CalendarEvent", back_populates="calendar", cascade="all, delete-orphan")

class CalendarPermission(Base):
    __tablename__ = "calendar_permissions"

    id = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("shared_calendars.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)  # Discord user ID
    permission_level = Column(String, nullable=False)  # "reader", "writer", "owner"
    granted_at = Column(DateTime, default=datetime.utcnow)
    granted_by = Column(BigInteger, nullable=False)  # Discord user ID who granted permission

    # Relationships
    calendar = relationship("SharedCalendar", back_populates="permissions")

    # Unique constraint to prevent duplicate permissions
    __table_args__ = (UniqueConstraint('calendar_id', 'user_id', name='unique_calendar_user_permission'),)

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("shared_calendars.id"), nullable=False)
    google_event_id = Column(String, nullable=True)  # Google Calendar event ID
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_by = Column(BigInteger, nullable=False)  # Discord user ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    calendar = relationship("SharedCalendar", back_populates="events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")

class EventAttendee(Base):
    __tablename__ = "event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)  # Discord user ID
    role_name = Column(String, nullable=True)  # Role that was assigned to this event
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("CalendarEvent", back_populates="attendees")

    # Unique constraint to prevent duplicate attendees
    __table_args__ = (UniqueConstraint('event_id', 'user_id', name='unique_event_attendee'),)
