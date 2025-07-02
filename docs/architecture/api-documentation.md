# **📚 API Documentation**

This document provides comprehensive API documentation for the Discord Bot services and components.

---

## **📋 Table of Contents**

1. [Core Services](#core-services)
2. [Calendar Service API](#calendar-service-api)
3. [Reminder Service API](#reminder-service-api)
4. [User Service API](#user-service-api)
5. [Service Container API](#service-container-api)
6. [Command System API](#command-system-api)
7. [Error Handling](#error-handling)

---

## **🏗️ Core Services**

### **Service Registration Pattern**

All services follow the same registration pattern in their respective features:

```python
async def register_services(self):
    """Register feature services with the container"""
    service = MyService()
    self.container.register_singleton("my_service", service)
```

### **Service Access Pattern**

Services are accessed consistently across all commands:

```python
async def execute_command(self, interaction, **kwargs):
    service = self.bot.services.get("service_name")
    result = await service.method_name(**kwargs)
```

---

## **📅 Calendar Service API**

### **Class**: `CalendarService`

**Location**: `src/features/calendar/services/calendar_service.py`

#### **Public Methods**

##### `validate_calendar_id(calendar_id: str) -> bool`
```python
"""
Validate Google Calendar ID format.

Args:
    calendar_id (str): Calendar ID to validate (should be email-like)

Returns:
    bool: True if valid format, False otherwise

Example:
    >>> service.validate_calendar_id("user@gmail.com")
    True
    >>> service.validate_calendar_id("invalid")
    False
"""
```

##### `link_user_calendar(user_id: int, calendar_id: str) -> bool`
```python
"""
Link a user's Discord account to their Google Calendar.

Args:
    user_id (int): Discord user ID
    calendar_id (str): Google Calendar ID

Returns:
    bool: True if successfully linked, False otherwise

Raises:
    ValidationError: If calendar_id format is invalid
    DatabaseError: If database operation fails

Example:
    >>> await service.link_user_calendar(123456789, "user@gmail.com")
    True
"""
```

##### `create_calendar(name: str, creator_id: int, description: str = "", google_calendar_id: str = "") -> Calendar`
```python
"""
Create a new shared calendar.

Args:
    name (str): Calendar display name
    creator_id (int): Discord user ID of creator
    description (str, optional): Calendar description
    google_calendar_id (str, optional): Associated Google Calendar ID

Returns:
    Calendar: Created calendar object

Raises:
    CalendarExistsError: If calendar with same name exists
    PermissionError: If user lacks creation permissions
    DatabaseError: If database operation fails

Example:
    >>> calendar = await service.create_calendar(
    ...     name="Team Events",
    ...     creator_id=123456789,
    ...     description="Monthly team meetings"
    ... )
"""
```

##### `get_calendar(calendar_name: str) -> Calendar | None`
```python
"""
Retrieve calendar by name.

Args:
    calendar_name (str): Name of the calendar

Returns:
    Calendar | None: Calendar object if found, None otherwise

Example:
    >>> calendar = await service.get_calendar("Team Events")
    >>> if calendar:
    ...     print(f"Found calendar: {calendar.name}")
"""
```

##### `add_permission(calendar_id: int, user_id: int, permission: str, admin_id: int) -> bool`
```python
"""
Add user permission to calendar.

Args:
    calendar_id (int): Internal calendar ID
    user_id (int): Discord user ID to grant permission
    permission (str): Permission level ('reader', 'writer', 'owner')
    admin_id (int): Discord user ID of admin granting permission

Returns:
    bool: True if permission granted successfully

Raises:
    CalendarNotFoundError: If calendar doesn't exist
    PermissionError: If admin lacks permission to grant access
    ValidationError: If permission level is invalid

Example:
    >>> success = await service.add_permission(
    ...     calendar_id=1,
    ...     user_id=987654321,
    ...     permission="writer",
    ...     admin_id=123456789
    ... )
"""
```

##### `create_event(calendar_id: int, event_data: dict) -> Event`
```python
"""
Create a new calendar event.

Args:
    calendar_id (int): Internal calendar ID
    event_data (dict): Event details containing:
        - name (str): Event title
        - start_time (datetime): Event start time
        - end_time (datetime): Event end time
        - location (str, optional): Event location
        - description (str, optional): Event description
        - attendees (list, optional): List of user IDs

Returns:
    Event: Created event object

Raises:
    CalendarNotFoundError: If calendar doesn't exist
    PermissionError: If user lacks write access
    ValidationError: If event data is invalid
    TimeConflictError: If event conflicts with existing events

Example:
    >>> event = await service.create_event(1, {
    ...     "name": "Team Meeting",
    ...     "start_time": datetime(2024, 1, 15, 14, 0),
    ...     "end_time": datetime(2024, 1, 15, 15, 0),
    ...     "location": "Conference Room A",
    ...     "description": "Weekly team sync",
    ...     "attendees": [123456789, 987654321]
    ... })
"""
```

##### `find_free_slots(user_id: int, start_dt: datetime, end_dt: datetime, duration: int) -> list[dict]`
```python
"""
Find available time slots for a user.

Args:
    user_id (int): Discord user ID
    start_dt (datetime): Search start time
    end_dt (datetime): Search end time
    duration (int): Required slot duration in minutes

Returns:
    list[dict]: List of available slots, each containing:
        - start (datetime): Slot start time
        - end (datetime): Slot end time
        - duration (int): Slot duration in minutes

Raises:
    CalendarNotLinkedError: If user has no linked calendar
    ValidationError: If parameters are invalid

Example:
    >>> slots = await service.find_free_slots(
    ...     user_id=123456789,
    ...     start_dt=datetime(2024, 1, 15, 9, 0),
    ...     end_dt=datetime(2024, 1, 15, 17, 0),
    ...     duration=60
    ... )
    >>> print(f"Found {len(slots)} available slots")
"""
```

##### `visualize_period(calendar_name: str, start_dt: datetime, end_dt: datetime) -> str`
```python
"""
Generate visual representation of calendar period.

Args:
    calendar_name (str): Name of calendar to visualize
    start_dt (datetime): Period start date
    end_dt (datetime): Period end date

Returns:
    str: ASCII art visualization of the calendar period

Raises:
    CalendarNotFoundError: If calendar doesn't exist
    PermissionError: If user lacks read access
    ValidationError: If period is too long (>30 days)

Example:
    >>> visualization = await service.visualize_period(
    ...     calendar_name="Team Events",
    ...     start_dt=datetime(2024, 1, 15),
    ...     end_dt=datetime(2024, 1, 20)
    ... )
"""
```

#### **Permission Levels**

- **reader**: Can view calendar and events
- **writer**: Can create, edit, and delete events
- **owner**: Full calendar management including user permissions

---

## **⏰ Reminder Service API**

### **Class**: `ReminderService`

**Location**: `src/features/reminders/services/reminder_service.py`

#### **Public Methods**

##### `create_template(template_data: dict) -> ReminderTemplate`
```python
"""
Create a reusable reminder template.

Args:
    template_data (dict): Template configuration containing:
        - name (str): Template name
        - message (str): Reminder message template
        - timing (dict): Default timing configuration
        - target_type (str): Type of target ('poll', 'event', 'custom')

Returns:
    ReminderTemplate: Created template object

Example:
    >>> template = await service.create_template({
    ...     "name": "poll_reminder",
    ...     "message": "Poll '{poll_name}' ends in {time_remaining}!",
    ...     "timing": {"before_end": "1h"},
    ...     "target_type": "poll"
    ... })
"""
```

##### `set_reminder(reminder_data: dict) -> Reminder`
```python
"""
Set a custom reminder.

Args:
    reminder_data (dict): Reminder configuration containing:
        - user_id (int): Discord user ID
        - message (str): Reminder message
        - trigger_time (datetime): When to send reminder
        - target_id (str, optional): Associated target ID
        - template_name (str, optional): Template to use

Returns:
    Reminder: Created reminder object

Example:
    >>> reminder = await service.set_reminder({
    ...     "user_id": 123456789,
    ...     "message": "Meeting starts in 15 minutes",
    ...     "trigger_time": datetime(2024, 1, 15, 13, 45),
    ...     "target_id": "event_123"
    ... })
"""
```

##### `get_user_reminders(user_id: int) -> list[Reminder]`
```python
"""
Get all active reminders for a user.

Args:
    user_id (int): Discord user ID

Returns:
    list[Reminder]: List of user's active reminders

Example:
    >>> reminders = await service.get_user_reminders(123456789)
    >>> print(f"User has {len(reminders)} active reminders")
"""
```

##### `cancel_reminder(reminder_id: int, user_id: int) -> bool`
```python
"""
Cancel a specific reminder.

Args:
    reminder_id (int): Reminder ID to cancel
    user_id (int): Discord user ID (must own reminder)

Returns:
    bool: True if cancelled successfully

Raises:
    ReminderNotFoundError: If reminder doesn't exist
    PermissionError: If user doesn't own reminder

Example:
    >>> success = await service.cancel_reminder(456, 123456789)
"""
```

##### `get_reminder_logs(user_id: int, limit: int = 50) -> list[ReminderLog]`
```python
"""
Get reminder execution logs for a user.

Args:
    user_id (int): Discord user ID
    limit (int): Maximum number of logs to return

Returns:
    list[ReminderLog]: List of reminder execution logs

Example:
    >>> logs = await service.get_reminder_logs(123456789, limit=10)
    >>> for log in logs:
    ...     print(f"Reminder sent: {log.message} at {log.sent_at}")
"""
```

---

## **👥 User Service API**

### **Class**: `UserService`

**Location**: `src/features/users/services/user_service.py`

#### **Public Methods**

##### `get_user_status(user_id: int) -> dict`
```python
"""
Get comprehensive user status information.

Args:
    user_id (int): Discord user ID

Returns:
    dict: User status containing:
        - calendar_linked (bool): Whether user has linked calendar
        - active_reminders (int): Number of active reminders
        - preferences (dict): User preferences
        - last_activity (datetime): Last bot interaction

Example:
    >>> status = await service.get_user_status(123456789)
    >>> print(f"Calendar linked: {status['calendar_linked']}")
"""
```

##### `set_preference(user_id: int, key: str, value: Any) -> bool`
```python
"""
Set a user preference.

Args:
    user_id (int): Discord user ID
    key (str): Preference key
    value (Any): Preference value (will be JSON serialized)

Returns:
    bool: True if preference was set successfully

Example:
    >>> await service.set_preference(123456789, "timezone", "UTC-8")
    >>> await service.set_preference(123456789, "notifications", True)
"""
```

##### `get_preference(user_id: int, key: str, default: Any = None) -> Any`
```python
"""
Get a user preference value.

Args:
    user_id (int): Discord user ID
    key (str): Preference key
    default (Any): Default value if preference not found

Returns:
    Any: Preference value or default

Example:
    >>> timezone = await service.get_preference(123456789, "timezone", "UTC")
    >>> notifications = await service.get_preference(123456789, "notifications", False)
"""
```

##### `list_preferences(user_id: int) -> dict`
```python
"""
Get all preferences for a user.

Args:
    user_id (int): Discord user ID

Returns:
    dict: All user preferences as key-value pairs

Example:
    >>> prefs = await service.list_preferences(123456789)
    >>> for key, value in prefs.items():
    ...     print(f"{key}: {value}")
"""
```

##### `clear_preferences(user_id: int) -> int`
```python
"""
Clear all preferences for a user.

Args:
    user_id (int): Discord user ID

Returns:
    int: Number of preferences that were cleared

Example:
    >>> cleared = await service.clear_preferences(123456789)
    >>> print(f"Cleared {cleared} preferences")
"""
```

---

## **🔧 Service Container API**

### **Class**: `ServiceContainer`

**Location**: `src/core/service_container.py`

#### **Public Methods**

##### `register_singleton(interface: Union[Type[T], str], instance: T)`
```python
"""
Register a singleton service instance.

Args:
    interface: Type or string identifier for the service
    instance: Service instance to register

Example:
    >>> container.register_singleton("calendar_service", CalendarService())
    >>> container.register_singleton(CalendarService, calendar_instance)
"""
```

##### `register_factory(interface: Union[Type[T], str], factory: Callable[[], T])`
```python
"""
Register a factory function for service creation.

Args:
    interface: Type or string identifier for the service
    factory: Function that creates service instances

Example:
    >>> container.register_factory("calendar_service", lambda: CalendarService())
"""
```

##### `get(interface: Union[Type[T], str]) -> T`
```python
"""
Get a service instance by interface.

Args:
    interface: Type or string identifier for the service

Returns:
    T: Service instance

Raises:
    ServiceNotFoundError: If service is not registered

Example:
    >>> calendar_service = container.get("calendar_service")
    >>> user_service = container.get(UserService)
"""
```

---

## **⚡ Command System API**

### **Abstract Class**: `BaseCommand`

**Location**: `src/core/base_command.py`

#### **Required Implementation Methods**

##### `async def process_command(self, interaction: discord.Interaction, data: Dict[str, Any]) -> CommandResult`
```python
"""
Implement the main business logic for the command.

Args:
    interaction: Discord interaction object
    data: Validated command data

Returns:
    CommandResult: Result of command execution

Example:
    async def process_command(self, interaction, data):
        service = self.bot.services.get("my_service")
        result = await service.do_something(data['param'])
        return CommandResult(success=True, data=result)
"""
```

#### **Optional Override Methods**

##### `async def validate_input(self, interaction: discord.Interaction, **kwargs) -> Dict[str, Any]`
```python
"""
Validate and transform command input.

Args:
    interaction: Discord interaction object
    **kwargs: Command parameters

Returns:
    dict: Validation result with 'valid', 'data', and optionally 'errors'

Example:
    async def validate_input(self, interaction, name: str, **kwargs):
        if not name.strip():
            return {'valid': False, 'errors': ['Name is required']}
        return {'valid': True, 'data': {'name': name.strip()}}
"""
```

##### `async def send_response(self, interaction: discord.Interaction, result: CommandResult)`
```python
"""
Send custom response to Discord.

Args:
    interaction: Discord interaction object
    result: Command execution result

Example:
    async def send_response(self, interaction, result):
        if result.success:
            embed = EmbedBuilder().success("Done!", result.message).build()
        else:
            embed = EmbedBuilder().error("Error", result.error).build()
        await interaction.response.send_message(embed=embed)
"""
```

---

## **🚫 Error Handling**

### **Exception Hierarchy**

```python
BotError                           # Base exception
├── ServiceError                   # Service-related errors
│   ├── ServiceNotFoundError      # Service not registered
│   └── ServiceInitializationError # Service startup failed
├── ValidationError                # Input validation errors
├── PermissionError               # Access denied errors
├── CalendarError                 # Calendar-specific errors
│   ├── CalendarNotFoundError     # Calendar doesn't exist
│   ├── CalendarExistsError       # Calendar already exists
│   ├── CalendarNotLinkedError    # User calendar not linked
│   └── TimeConflictError         # Event time conflicts
├── ReminderError                 # Reminder-specific errors
│   ├── ReminderNotFoundError     # Reminder doesn't exist
│   └── TemplateNotFoundError     # Template doesn't exist
└── DatabaseError                 # Database operation errors
```

### **Error Response Format**

All errors follow a consistent format in Discord responses:

```python
{
    "success": False,
    "error": "Error Type",
    "message": "Human-readable error description",
    "details": {  # Optional additional details
        "field": "validation error details",
        "suggestions": ["Try this", "Or this"]
    }
}
```

### **Error Handling in Commands**

```python
try:
    result = await service.some_operation()
    return CommandResult(success=True, data=result)
except CalendarNotFoundError:
    return CommandResult(
        success=False,
        error="Calendar not found. Please check the name and try again."
    )
except PermissionError:
    return CommandResult(
        success=False,
        error="You don't have permission to perform this action."
    )
except Exception as e:
    # Log the full error for debugging
    logger.error(f"Unexpected error in command: {str(e)}")
    return CommandResult(
        success=False,
        error="An unexpected error occurred. Please try again later."
    )
```

---

## **🎯 Usage Examples**

### **Creating a New Command**

```python
from src.core.base_command import BaseCommand, CommandResult

class MyNewCommand(BaseCommand):
    async def validate_input(self, interaction, name: str, **kwargs):
        if not name.strip():
            return {'valid': False, 'errors': ['Name is required']}
        return {'valid': True, 'data': {'name': name.strip()}}

    async def process_command(self, interaction, data):
        service = self.bot.services.get("my_service")
        result = await service.create_something(data['name'])
        return CommandResult(success=True, data=result)
```

### **Registering Services in Features**

```python
class MyFeature(BaseFeature):
    async def register_services(self):
        service = MyService()
        self.container.register_singleton("my_service", service)

    async def register_commands(self):
        command = MyNewCommand()
        await self.bot.tree.add_command(app_commands.Command(
            name="my_command",
            description="Does something useful",
            callback=command.execute
        ))
```

This API documentation provides the foundation for developing with and extending the Discord Bot's service architecture.