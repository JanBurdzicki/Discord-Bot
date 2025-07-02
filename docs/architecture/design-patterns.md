# **🎨 Design Patterns and OOP Practices**

This document describes the design patterns, architectural principles, and object-oriented programming practices implemented in the Discord Bot refactor.

---

## **📋 Table of Contents**

1. [Core Design Patterns](#core-design-patterns)
2. [Architectural Patterns](#architectural-patterns)
3. [OOP Principles Applied](#oop-principles-applied)
4. [Code Organization Patterns](#code-organization-patterns)
5. [Best Practices Implementation](#best-practices-implementation)

---

## **🏗️ Core Design Patterns**

### **1. Template Method Pattern**

**Location**: `src/core/base_command.py`
**Purpose**: Define command execution skeleton while allowing subclasses to customize specific steps.

```python
class BaseCommand(ABC):
    async def execute(self, interaction: discord.Interaction, **kwargs) -> None:
        """Template method defining execution flow"""
        try:
            await self.pre_execute(interaction, **kwargs)
            if not await self._check_permissions(interaction):
                return await self._send_permission_error(interaction)
            validation_result = await self.validate_input(interaction, **kwargs)
            if not validation_result.get('valid', True):
                return await self._send_validation_error(interaction, validation_result.get('errors', []))
            result = await self.process_command(interaction, validation_result.get('data', kwargs))
            await self.send_response(interaction, result)
            await self.post_execute(interaction, result)
        except Exception as e:
            await self._handle_command_error(interaction, e)

    @abstractmethod
    async def process_command(self, interaction, data) -> CommandResult:
        """Subclasses implement business logic here"""
        pass
```

**Benefits**:
- Consistent command execution flow
- Extensible validation and error handling
- Separation of concerns between framework and business logic
- Reduced code duplication across commands

### **2. Dependency Injection Pattern**

**Location**: `src/core/service_container.py`
**Purpose**: Manage dependencies and promote loose coupling between components.

```python
class ServiceContainer:
    def __init__(self):
        self._services = {}
        self._singletons = {}
        self._factories = {}

    def register_singleton(self, interface: Union[Type[T], str], instance: T):
        """Register a singleton instance"""
        self._singletons[interface] = instance

    def get(self, interface: Union[Type[T], str]) -> T:
        """Resolve service by interface"""
        # Implementation handles singletons, factories, and type resolution
```

**Usage in Features**:
```python
class CalendarFeature(BaseFeature):
    async def register_services(self):
        calendar_service = CalendarService()
        self.container.register_singleton("calendar_service", calendar_service)
```

**Benefits**:
- Decoupled service dependencies
- Easy testing with mock services
- Centralized service lifecycle management
- Support for singletons and factories

### **3. Builder Pattern**

**Location**: `src/core/builders.py`
**Purpose**: Construct complex Discord embeds with fluent interface.

```python
class EmbedBuilder:
    def __init__(self):
        self._embed = discord.Embed()

    def set_title(self, title: str):
        self._embed.title = title
        return self

    def set_description(self, description: str):
        self._embed.description = description
        return self

    def set_color(self, color: str):
        # Color mapping logic
        return self

    def build(self) -> discord.Embed:
        return self._embed
```

**Usage**:
```python
embed = (EmbedBuilder()
         .set_title("✅ Success")
         .set_description("Operation completed successfully")
         .set_color("green")
         .add_field("Details", "Calendar created")
         .build())
```

**Benefits**:
- Fluent, readable embed construction
- Consistent visual styling
- Encapsulated complex embed logic
- Reusable across all features

### **4. Factory Pattern**

**Location**: Feature registration and service creation
**Purpose**: Create objects without specifying exact classes.

```python
class FeatureFactory:
    @staticmethod
    def create_features(bot, container):
        return [
            CalendarFeature(bot, container),
            ReminderFeature(bot, container),
            PollFeature(bot, container),
            # ... other features
        ]
```

**Benefits**:
- Centralized object creation
- Easy to add new features
- Consistent initialization patterns

### **5. Observer Pattern**

**Location**: Event listeners and Discord event handling
**Purpose**: Notify multiple components of state changes.

```python
class ReminderFeature(BaseFeature):
    async def register_listeners(self):
        @self.bot.event
        async def on_reaction_add(reaction, user):
            # Handle poll voting via reactions
            await self.handle_poll_reaction(reaction, user)
```

**Benefits**:
- Loose coupling between event sources and handlers
- Multiple features can respond to same events
- Easy to add new event handlers

---

## **🏛️ Architectural Patterns**

### **1. Layered Architecture**

```
┌─────────────────┐
│   Discord API   │  ← External Interface
├─────────────────┤
│   Bot Core      │  ← Application Layer
├─────────────────┤
│   Features      │  ← Business Logic Layer
├─────────────────┤
│   Services      │  ← Service Layer
├─────────────────┤
│   Data Models   │  ← Data Access Layer
└─────────────────┘
```

**Benefits**:
- Clear separation of concerns
- Easy to test individual layers
- Maintainable and extensible architecture

### **2. Plugin Architecture**

**Features as Plugins**: Each feature is self-contained and registers independently.

```python
class BaseFeature(ABC):
    async def register_commands(self):
        """Register Discord commands"""
        pass

    async def register_services(self):
        """Register feature services"""
        pass

    async def register_listeners(self):
        """Register event listeners"""
        pass
```

**Benefits**:
- Modular design
- Features can be enabled/disabled independently
- Easy to add new features without modifying core

### **3. Service-Oriented Architecture (SOA)**

Services provide specific functionality across features:

- **CalendarService**: Calendar management operations
- **ReminderService**: Reminder scheduling and execution
- **UserService**: User preference and profile management
- **PollService**: Poll creation and voting logic

**Benefits**:
- Reusable business logic
- Clear service boundaries
- Easy to mock for testing

---

## **🎯 OOP Principles Applied**

### **1. Encapsulation**

**Data Hiding**: Internal implementation details are hidden behind public interfaces.

```python
class CalendarService:
    def __init__(self):
        self._google_api = GoogleCalendarAPI()  # Private implementation
        self._cache = {}  # Internal caching

    async def create_event(self, calendar_id: str, event_data: dict):
        """Public interface for event creation"""
        return await self._google_api.create_event(calendar_id, event_data)
```

**Benefits**:
- Internal changes don't affect external code
- Clear public interfaces
- Protected against misuse

### **2. Inheritance**

**Base Classes**: Common functionality shared through inheritance.

```python
# Base command for all commands
class BaseCommand(ABC)

# Base feature for all features
class BaseFeature(ABC)

# Specialized commands inherit common behavior
class CreatePollCommand(BaseCommand)
class AddEventCommand(BaseCommand)
```

**Benefits**:
- Code reuse
- Consistent interfaces
- Polymorphic behavior

### **3. Polymorphism**

**Interface-based Design**: Objects of different types can be used interchangeably.

```python
# All commands implement the same interface
commands = [
    CreatePollCommand(),
    AddEventCommand(),
    SetReminderCommand()
]

for command in commands:
    await command.execute(interaction, **kwargs)  # Polymorphic call
```

**Benefits**:
- Flexible and extensible code
- Easy to add new command types
- Uniform handling of different objects

### **4. Abstraction**

**Abstract Base Classes**: Define contracts without implementation.

```python
class BaseCommand(ABC):
    @abstractmethod
    async def process_command(self, interaction, data) -> CommandResult:
        """Subclasses must implement business logic"""
        pass

    @abstractmethod
    async def validate_input(self, interaction, **kwargs) -> Dict[str, Any]:
        """Subclasses define validation rules"""
        pass
```

**Benefits**:
- Clear contracts and interfaces
- Enforced implementation of required methods
- Consistent behavior across implementations

---

## **📁 Code Organization Patterns**

### **1. Feature-based Organization**

```
src/
├── features/
│   ├── calendar/
│   │   ├── __init__.py
│   │   ├── calendar_feature.py
│   │   ├── commands/
│   │   └── services/
│   ├── reminders/
│   └── polls/
```

**Benefits**:
- Related code grouped together
- Easy to locate feature-specific code
- Clear module boundaries

### **2. Separation of Concerns**

Each module has a single responsibility:

- **Commands**: Handle Discord interactions
- **Services**: Implement business logic
- **Models**: Define data structures
- **Validators**: Handle input validation
- **Builders**: Construct complex objects

### **3. Configuration Management**

Environment-specific settings separated from code:

```python
# Environment variables for configuration
DATABASE_URL = os.getenv('DATABASE_URL')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
```

---

## **🔧 Best Practices Implementation**

### **1. Error Handling**

**Consistent Error Handling**: All commands use the same error handling pattern.

```python
try:
    result = await self.process_command(interaction, data)
    await self.send_response(interaction, result)
except ValidationError as e:
    await self._send_validation_error(interaction, e.errors)
except PermissionError as e:
    await self._send_permission_error(interaction)
except Exception as e:
    await self._handle_command_error(interaction, e)
```

### **2. Input Validation**

**Centralized Validation**: Reusable validation functions.

```python
def validate_required(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValidationError(f"{field_name} is required")
    return value.strip()

def validate_integer(value: str, field_name: str, min_val: int = None, max_val: int = None) -> int:
    # Integer validation with range checking
```

### **3. Async/Await Pattern**

**Consistent Async Usage**: All I/O operations use async/await.

```python
async def create_calendar(self, name: str, creator_id: int) -> Calendar:
    async with AsyncSessionLocal() as session:
        calendar = Calendar(name=name, creator_id=creator_id)
        session.add(calendar)
        await session.commit()
        return calendar
```

### **4. Testing Patterns**

**Comprehensive Testing**: Unit tests, integration tests, and mocking.

```python
@pytest.fixture
def mock_service_container():
    container = ServiceContainer()
    calendar_service = AsyncMock()
    container.register_singleton("calendar_service", calendar_service)
    return container, {"calendar": calendar_service}

@pytest.mark.asyncio
async def test_command_execution(mock_service_container):
    # Test implementation
```

### **5. Documentation Standards**

**Consistent Documentation**: All classes and methods are documented.

```python
class CalendarService:
    """
    Service for managing calendar operations.

    Handles Google Calendar API interactions, calendar permissions,
    and event management for Discord bot users.
    """

    async def create_event(self, calendar_id: str, event_data: dict) -> Event:
        """
        Create a new calendar event.

        Args:
            calendar_id: The ID of the calendar to create event in
            event_data: Dictionary containing event details

        Returns:
            Event: The created event object

        Raises:
            CalendarNotFoundError: If calendar doesn't exist
            PermissionError: If user lacks write access
        """
```

---

## **🎉 Summary**

The Discord Bot refactor implements multiple design patterns and OOP principles to create a maintainable, extensible, and testable codebase:

### **Key Patterns Used:**
- **Template Method** for consistent command execution
- **Dependency Injection** for loose coupling
- **Builder** for complex object construction
- **Factory** for object creation
- **Observer** for event handling

### **Architecture Benefits:**
- **Modular Design**: Features are independent and self-contained
- **Separation of Concerns**: Clear responsibility boundaries
- **Testability**: Comprehensive testing with mocking support
- **Maintainability**: Clean code structure and documentation
- **Extensibility**: Easy to add new features and commands

This architectural foundation provides a robust base for future development and ensures the bot can scale and evolve with changing requirements.