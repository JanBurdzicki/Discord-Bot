"""
Input validation system for commands.
Provides common validators and a base class for custom validators.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union, Pattern, Tuple
from datetime import datetime, timedelta
import re
import discord

class ValidationError(Exception):
    """Raised when validation fails"""
    pass

class BaseValidator(ABC):
    """Base class for all validators"""

    @abstractmethod
    async def validate(self, value: Any) -> Any:
        """Validate the input and return the processed value"""
        pass

class StringValidator(BaseValidator):
    """Validates string inputs with optional constraints"""

    def __init__(self, min_length: int = 0, max_length: int = None, pattern: Pattern = None,
                 not_empty: bool = True, strip: bool = True):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.not_empty = not_empty
        self.strip = strip

    async def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value).__name__}")

        if self.strip:
            value = value.strip()

        if self.not_empty and not value:
            raise ValidationError("Value cannot be empty")

        if len(value) < self.min_length:
            raise ValidationError(f"Minimum length is {self.min_length} characters")

        if self.max_length and len(value) > self.max_length:
            raise ValidationError(f"Maximum length is {self.max_length} characters")

        if self.pattern and not self.pattern.match(value):
            raise ValidationError("Value does not match required format")

        return value

class IntegerValidator(BaseValidator):
    """Validates integer inputs with optional range constraints"""

    def __init__(self, min_value: int = None, max_value: int = None):
        self.min_value = min_value
        self.max_value = max_value

    async def validate(self, value: Any) -> int:
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValidationError(f"'{value}' is not a valid integer")
        elif not isinstance(value, int):
            raise ValidationError(f"Expected integer, got {type(value).__name__}")

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"Value must be at least {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"Value must be at most {self.max_value}")

        return value

class DateTimeValidator(BaseValidator):
    """Validates datetime strings and converts them to datetime objects"""

    def __init__(self, formats: List[str] = None, future_only: bool = False, past_only: bool = False):
        self.formats = formats or [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y"
        ]
        self.future_only = future_only
        self.past_only = past_only

    async def validate(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = None
            for fmt in self.formats:
                try:
                    dt = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                formats_str = ", ".join(self.formats)
                raise ValidationError(f"Invalid datetime format. Use one of: {formats_str}")
        else:
            raise ValidationError(f"Expected datetime or string, got {type(value).__name__}")

        now = datetime.now()

        if self.future_only and dt <= now:
            raise ValidationError("DateTime must be in the future")

        if self.past_only and dt >= now:
            raise ValidationError("DateTime must be in the past")

        return dt

class EmailValidator(BaseValidator):
    """Validates email addresses"""

    def __init__(self):
        # Simple email regex - not perfect but good enough for most cases
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

    async def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"Expected string, got {type(value).__name__}")

        value = value.strip().lower()

        if not self.email_pattern.match(value):
            raise ValidationError("Invalid email address format")

        return value

class ChoiceValidator(BaseValidator):
    """Validates that value is one of the allowed choices"""

    def __init__(self, choices: List[Any], case_sensitive: bool = True):
        self.choices = choices
        self.case_sensitive = case_sensitive
        if not case_sensitive and all(isinstance(c, str) for c in choices):
            self.lower_choices = [c.lower() for c in choices]

    async def validate(self, value: Any) -> Any:
        if self.case_sensitive:
            if value not in self.choices:
                choices_str = ", ".join(str(c) for c in self.choices)
                raise ValidationError(f"Value must be one of: {choices_str}")
            return value
        else:
            if isinstance(value, str):
                value_lower = value.lower()
                if value_lower in self.lower_choices:
                    # Return the original case from choices
                    return self.choices[self.lower_choices.index(value_lower)]

            choices_str = ", ".join(str(c) for c in self.choices)
            raise ValidationError(f"Value must be one of: {choices_str}")

class ListValidator(BaseValidator):
    """Validates comma-separated lists"""

    def __init__(self, item_validator: BaseValidator = None, min_items: int = 0,
                 max_items: int = None, separator: str = ","):
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        self.separator = separator

    async def validate(self, value: Any) -> List[Any]:
        if isinstance(value, str):
            if not value.strip():
                items = []
            else:
                items = [item.strip() for item in value.split(self.separator) if item.strip()]
        elif isinstance(value, list):
            items = value
        else:
            raise ValidationError(f"Expected string or list, got {type(value).__name__}")

        if len(items) < self.min_items:
            raise ValidationError(f"At least {self.min_items} items required")

        if self.max_items and len(items) > self.max_items:
            raise ValidationError(f"At most {self.max_items} items allowed")

        if self.item_validator:
            validated_items = []
            for i, item in enumerate(items):
                try:
                    validated_item = await self.item_validator.validate(item)
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f"Item {i+1}: {str(e)}")
            return validated_items

        return items

# Common validator instances
calendar_name_validator = StringValidator(min_length=1, max_length=50, not_empty=True)
description_validator = StringValidator(max_length=500, not_empty=False)
email_validator = EmailValidator()
positive_integer_validator = IntegerValidator(min_value=1)
poll_option_validator = StringValidator(min_length=1, max_length=100)
future_datetime_validator = DateTimeValidator(future_only=True)

# Factory functions for commonly used validators
def validate_calendar_name(value: str) -> str:
    """Validate calendar name"""
    validator = StringValidator(min_length=1, max_length=50, not_empty=True)
    return validator.validate(value)

def validate_poll_options(value: str) -> List[str]:
    """Validate comma-separated poll options"""
    validator = ListValidator(
        item_validator=StringValidator(min_length=1, max_length=100),
        min_items=2,
        max_items=20
    )
    return validator.validate(value)

def validate_positive_integer(value: Union[str, int]) -> int:
    """Validate positive integer"""
    validator = IntegerValidator(min_value=1)
    return validator.validate(value)

def validate_datetime_string(value: str) -> datetime:
    """Validate datetime string"""
    validator = DateTimeValidator()
    return validator.validate(value)

def validate_email_address(value: str) -> str:
    """Validate email address"""
    validator = EmailValidator()
    return validator.validate(value)

# Async wrapper functions for use with decorators
async def async_validate_calendar_name(value: str) -> str:
    return await calendar_name_validator.validate(value)

async def async_validate_poll_options(value: str) -> List[str]:
    validator = ListValidator(
        item_validator=poll_option_validator,
        min_items=2,
        max_items=20
    )
    return await validator.validate(value)

async def async_validate_positive_integer(value: Union[str, int]) -> int:
    return await positive_integer_validator.validate(value)

async def async_validate_future_datetime(value: str) -> datetime:
    return await future_datetime_validator.validate(value)

async def async_validate_email(value: str) -> str:
    return await email_validator.validate(value)

# ========== Validation Decorators ==========

def validate_required(field_name: str):
    """Validator to ensure field is not empty"""
    def validator(value: Any) -> Any:
        if not value or (isinstance(value, str) and not value.strip()):
            raise ValidationError(f"{field_name} is required")
        return value
    return validator

def validate_length(min_length: int = None, max_length: int = None):
    """Validator to check string length"""
    def validator(value: str) -> str:
        if min_length and len(value) < min_length:
            raise ValidationError(f"Must be at least {min_length} characters long")
        if max_length and len(value) > max_length:
            raise ValidationError(f"Must be no more than {max_length} characters long")
        return value
    return validator

def validate_range(min_val: int = None, max_val: int = None):
    """Validator to check numeric range"""
    def validator(value: Union[int, float]) -> Union[int, float]:
        if min_val is not None and value < min_val:
            raise ValidationError(f"Must be at least {min_val}")
        if max_val is not None and value > max_val:
            raise ValidationError(f"Must be no more than {max_val}")
        return value
    return validator

# ========== Calendar Validators ==========

async def validate_calendar_name(name: str) -> str:
    """Validate calendar name"""
    name = name.strip()
    if not name:
        raise ValidationError("Calendar name cannot be empty")
    if len(name) > 100:
        raise ValidationError("Calendar name too long (max 100 characters)")
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationError("Calendar name contains invalid characters")
    return name

async def validate_event_title(title: str) -> str:
    """Validate event title"""
    title = title.strip()
    if not title:
        raise ValidationError("Event title cannot be empty")
    if len(title) > 200:
        raise ValidationError("Event title too long (max 200 characters)")
    return title

async def validate_datetime_string(dt_string: str, field_name: str = "datetime") -> datetime:
    """Validate and parse datetime string"""
    try:
        # Try common formats
        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(dt_string, fmt)
            except ValueError:
                continue
        raise ValueError("Invalid format")
    except ValueError:
        raise ValidationError(f"Invalid {field_name} format. Use YYYY-MM-DD HH:MM")

async def validate_email(email: str) -> str:
    """Validate email format"""
    email = email.strip().lower()
    if not email:
        raise ValidationError("Email cannot be empty")

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format")
    return email

async def validate_permission_level(level: str) -> str:
    """Validate calendar permission level"""
    level = level.lower().strip()
    valid_levels = ["reader", "writer", "owner"]
    if level not in valid_levels:
        raise ValidationError(f"Invalid permission level. Must be one of: {', '.join(valid_levels)}")
    return level

# ========== Poll Validators ==========

async def validate_poll_question(question: str) -> str:
    """Validate poll question"""
    question = question.strip()
    if not question:
        raise ValidationError("Poll question cannot be empty")
    if len(question) > 500:
        raise ValidationError("Poll question too long (max 500 characters)")
    return question

async def validate_poll_options(options: str) -> List[str]:
    """Validate and parse poll options"""
    if not options or not options.strip():
        raise ValidationError("Poll options cannot be empty")

    option_list = [opt.strip() for opt in options.split(",") if opt.strip()]

    if len(option_list) < 2:
        raise ValidationError("Poll must have at least 2 options")
    if len(option_list) > 20:
        raise ValidationError("Poll cannot have more than 20 options (Discord limit)")

    # Check for duplicate options
    if len(option_list) != len(set(option_list)):
        raise ValidationError("Poll options must be unique")

    # Check option length
    for i, option in enumerate(option_list):
        if len(option) > 100:
            raise ValidationError(f"Option {i+1} too long (max 100 characters)")
        if not option:
            raise ValidationError(f"Option {i+1} cannot be empty")

    return option_list

async def validate_poll_duration(duration: int) -> int:
    """Validate poll duration in minutes"""
    if duration < 1:
        raise ValidationError("Poll duration must be at least 1 minute")
    if duration > 10080:  # 7 days
        raise ValidationError("Poll duration cannot exceed 7 days")
    return duration

async def validate_poll_id(poll_id: str) -> str:
    """Validate poll ID format"""
    poll_id = poll_id.strip()
    if not poll_id:
        raise ValidationError("Poll ID cannot be empty")
    # Basic UUID validation
    if not re.match(r'^[a-f0-9\-]{36}$', poll_id):
        raise ValidationError("Invalid poll ID format")
    return poll_id

# ========== User Validators ==========

async def validate_discord_user(user: discord.Member) -> discord.Member:
    """Validate Discord user"""
    if not user:
        raise ValidationError("User not found")
    if user.bot:
        raise ValidationError("Cannot target bot users")
    return user

async def validate_user_preference_key(key: str) -> str:
    """Validate user preference key"""
    key = key.strip().lower()
    if not key:
        raise ValidationError("Preference key cannot be empty")
    if len(key) > 50:
        raise ValidationError("Preference key too long (max 50 characters)")
    if not re.match(r'^[a-z0-9_]+$', key):
        raise ValidationError("Preference key can only contain lowercase letters, numbers, and underscores")
    return key

async def validate_user_preference_value(value: str) -> str:
    """Validate user preference value"""
    if len(value) > 500:
        raise ValidationError("Preference value too long (max 500 characters)")
    return value

# ========== Reminder Validators ==========

async def validate_reminder_template_name(name: str) -> str:
    """Validate reminder template name"""
    name = name.strip()
    if not name:
        raise ValidationError("Template name cannot be empty")
    if len(name) > 100:
        raise ValidationError("Template name too long (max 100 characters)")
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationError("Template name contains invalid characters")
    return name

async def validate_reminder_message_template(template: str) -> str:
    """Validate reminder message template"""
    template = template.strip()
    if not template:
        raise ValidationError("Message template cannot be empty")
    if len(template) > 2000:
        raise ValidationError("Message template too long (max 2000 characters)")
    return template

async def validate_reminder_priority(priority: str) -> str:
    """Validate reminder priority"""
    priority = priority.lower().strip()
    valid_priorities = ["informational", "urgent", "very_urgent", "critical"]
    if priority not in valid_priorities:
        raise ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
    return priority

async def validate_reminder_trigger_type(trigger_type: str) -> str:
    """Validate reminder trigger type"""
    trigger_type = trigger_type.lower().strip()
    valid_types = ["specific_time", "time_before", "interval"]
    if trigger_type not in valid_types:
        raise ValidationError(f"Invalid trigger type. Must be one of: {', '.join(valid_types)}")
    return trigger_type

# ========== Role Validators ==========

async def validate_role_name(name: str) -> str:
    """Validate role name"""
    name = name.strip()
    if not name:
        raise ValidationError("Role name cannot be empty")
    if len(name) > 100:
        raise ValidationError("Role name too long (max 100 characters)")
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationError("Role name contains invalid characters")
    return name

async def validate_command_name(command: str) -> str:
    """Validate command name"""
    command = command.strip().lower()
    if not command:
        raise ValidationError("Command name cannot be empty")
    if not re.match(r'^[a-z_]+$', command):
        raise ValidationError("Command name can only contain lowercase letters and underscores")
    return command

# ========== Generic Validators ==========

def validate_integer(value: Union[int, str], min_val: int = None, max_val: int = None, field_name: str = "value") -> int:
    """Validate that a value is an integer within optional bounds"""
    try:
        int_val = int(value) if isinstance(value, str) else value
        if min_val is not None and int_val < min_val:
            raise ValidationError(f"{field_name} must be at least {min_val}")
        if max_val is not None and int_val > max_val:
            raise ValidationError(f"{field_name} must be at most {max_val}")
        return int_val
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid integer")

def validate_string_length(value: str, min_length: int = 0, max_length: int = None, field_name: str = "value") -> str:
    """Validate string length constraints"""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")

    value = value.strip()

    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long")

    if max_length is not None and len(value) > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters long")

    return value

async def validate_positive_integer(value: Union[int, str], field_name: str = "value") -> int:
    """Validate positive integer"""
    try:
        int_val = int(value)
        if int_val <= 0:
            raise ValidationError(f"{field_name} must be a positive integer")
        return int_val
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid integer")

async def validate_non_negative_integer(value: Union[int, str], field_name: str = "value") -> int:
    """Validate non-negative integer"""
    try:
        int_val = int(value)
        if int_val < 0:
            raise ValidationError(f"{field_name} must be a non-negative integer")
        return int_val
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid integer")

async def validate_text_length(text: str, min_length: int = 0, max_length: int = 2000, field_name: str = "text") -> str:
    """Validate text length"""
    text = text.strip()
    if len(text) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long")
    if len(text) > max_length:
        raise ValidationError(f"{field_name} must be no more than {max_length} characters long")
    return text

async def validate_comma_separated_integers(value: str, field_name: str = "values") -> List[int]:
    """Validate comma-separated list of integers"""
    if not value or not value.strip():
        return []

    try:
        int_list = [int(x.strip()) for x in value.split(",") if x.strip()]
        return int_list
    except ValueError:
        raise ValidationError(f"{field_name} must be comma-separated integers")

async def validate_comma_separated_strings(value: str, field_name: str = "values") -> List[str]:
    """Validate comma-separated list of strings"""
    if not value or not value.strip():
        return []

    string_list = [x.strip() for x in value.split(",") if x.strip()]
    return string_list

# ========== Complex Validators ==========

async def validate_time_range(start_time: str, end_time: str) -> Tuple[datetime, datetime]:
    """Validate that end time is after start time"""
    start_dt = await validate_datetime_string(start_time, "start time")
    end_dt = await validate_datetime_string(end_time, "end time")

    if end_dt <= start_dt:
        raise ValidationError("End time must be after start time")

    # Check if times are in the past (with some tolerance)
    now = datetime.utcnow()
    if start_dt < now - timedelta(minutes=5):
        raise ValidationError("Start time cannot be in the past")

    return start_dt, end_dt

async def validate_duration_minutes(duration: Union[int, str]) -> int:
    """Validate duration in minutes"""
    try:
        duration_int = int(duration)
        if duration_int < 1:
            raise ValidationError("Duration must be at least 1 minute")
        if duration_int > 525600:  # 1 year
            raise ValidationError("Duration cannot exceed 1 year")
        return duration_int
    except (ValueError, TypeError):
        raise ValidationError("Duration must be a valid number of minutes")

# ========== Utility Functions ==========

def format_validation_errors(errors: List[str]) -> str:
    """Format validation errors for display"""
    if not errors:
        return ""

    if len(errors) == 1:
        return f"❌ {errors[0]}"

    formatted = "❌ **Validation Errors:**\n"
    for i, error in enumerate(errors, 1):
        formatted += f"{i}. {error}\n"
    return formatted

def safe_validate(validator, value, default=None):
    """Safely run validator, returning default on error"""
    try:
        return validator(value)
    except (ValidationError, ValueError, TypeError):
        return default