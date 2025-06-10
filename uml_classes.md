## BotCore

```
+---------------------------------------------------------------+
|                          BotCore                              |
+---------------------------------------------------------------+
| - client: discord.Client                                      |
| - command_handler: CommandHandler                             |
| - calendar_service: CalendarService                           |
| - scheduler: ReminderScheduler                                |
| - user_manager: UserManager                                   |
| - ai_planner_agent: AIPlannerAgent                            |
| - poll_manager: PollManager                                   |
| - rule_engine: RuleEngine                                     |
| - permission_manager: PermissionManager                       |
| - stats_module: StatsModule                                   |
+---------------------------------------------------------------+
| + run() -> None                                               |
| + on_message(msg) -> None                                     |
| + register_events() -> None                                   |
+---------------------------------------------------------------+
```

## CommandHandler

```
+---------------------------------------------------------------+
|                      CommandHandler                           |
+---------------------------------------------------------------+
| - commands: dict[str, Callable]                               |
+---------------------------------------------------------------+
| + register(cmd: Command) -> None                              |
| + execute(ctx: CommandContext) -> Any                         |
| + load_custom_commands() -> None                              |
+---------------------------------------------------------------+
```

## CustomCommandManager

```
+---------------------------------------------------------------+
|                  CustomCommandManager                         |
+---------------------------------------------------------------+
| - user_defined_cmds: dict[str, str]                           |
+---------------------------------------------------------------+
| + add_command(name: str, code: str) -> None                   |
| + remove_command(name: str) -> None                           |
| + get_command(name: str) -> Optional[str]                     |
+---------------------------------------------------------------+
```

## CalendarService

```
+---------------------------------------------------------------+
|                     CalendarService                           |
+---------------------------------------------------------------+
| - credentials: OAuth2Credentials                              |
| - service: Resource                                           |
+---------------------------------------------------------------+
| + get_free_slots(user: UserProfile) -> list[TimeSlot]         |
| + add_event(event: CalendarEvent) -> str                      |
| + remove_event(event_id: str) -> bool                         |
| + update_event(event: CalendarEvent) -> bool                  |
+---------------------------------------------------------------+
```

## UserManager

```
+---------------------------------------------------------------+
|                        UserManager                            |
+---------------------------------------------------------------+
| - db: Session                                                 |
+---------------------------------------------------------------+
| + get_user(id: int) -> UserProfile                            |
| + update_preferences(id: int, prefs: dict) -> None            |
| + assign_roles(user: UserProfile) -> None                     |
+---------------------------------------------------------------+
```

## UserProfile

```
+---------------------------------------------------------------+
|                        UserProfile                            |
+---------------------------------------------------------------+
| - discord_id: int                                             |
| - calendar_email: str                                         |
| - preferences: dict                                           |
| - roles: list[str]                                            |
+---------------------------------------------------------------+
```

## ReminderScheduler

```
+---------------------------------------------------------------+
|                     ReminderScheduler                         |
+---------------------------------------------------------------+
| - job_store: dict[str, Job]                                   |
+---------------------------------------------------------------+
| + schedule(job: Callable, time: datetime) -> str              |
| + cancel(job_id: str) -> bool                                 |
| + load_jobs() -> None                                         |
+---------------------------------------------------------------+
```

## PollManager

```
+---------------------------------------------------------------+
|                        PollManager                            |
+---------------------------------------------------------------+
| - polls: dict[str, Poll]                                      |
+---------------------------------------------------------------+
| + create_poll(question: str, options: list[str], duration: int) -> str |
| + vote(poll_id: str, user_id: int, choice: int) -> None       |
| + get_results(poll_id: str) -> dict[str, int]                 |
+---------------------------------------------------------------+
```

## RuleEngine

```
+---------------------------------------------------------------+
|                         RuleEngine                            |
+---------------------------------------------------------------+
| - ruleset: str or list[str]                                   |
+---------------------------------------------------------------+
| + evaluate(conflicts: list[str]) -> bool                      |
| + suggest_resolution() -> list[str]                           |
| + explain_why_blocked() -> str                                |
+---------------------------------------------------------------+
```

## AIPlannerAgent

```
+---------------------------------------------------------------+
|                      AIPlannerAgent                           |
+---------------------------------------------------------------+
| - openai_key: str                                             |
| - prompt_templates: dict                                      |
+---------------------------------------------------------------+
| + suggest_times(users: list[UserProfile]) -> list[str]        |
| + summarize_schedule(user: UserProfile) -> str                |
| + resolve_conflicts(conflict_data: dict) -> str               |
+---------------------------------------------------------------+
```

## AvailabilityTracker

```
+---------------------------------------------------------------+
|                   AvailabilityTracker                         |
+---------------------------------------------------------------+
| - attendance_log: dict[int, list[datetime]]                   |
+---------------------------------------------------------------+
| + record_attendance(user_id: int, date: datetime) -> None     |
| + get_availability(user_id: int) -> float                     |
| + get_inactive_users() -> list[int]                           |
+---------------------------------------------------------------+
```

## StatsModule

```
+---------------------------------------------------------------+
|                        StatsModule                            |
+---------------------------------------------------------------+
| - usage_logs: list[dict]                                      |
+---------------------------------------------------------------+
| + log_usage(user_id: int, command: str) -> None               |
| + top_participants() -> list[UserProfile]                     |
| + get_stats_summary() -> dict                                 |
+---------------------------------------------------------------+
```

## PermissionManager

```
+---------------------------------------------------------------+
|                     PermissionManager                         |
+---------------------------------------------------------------+
| - role_permissions: dict[str, list[str]]                      |
+---------------------------------------------------------------+
| + can_execute(user: UserProfile, command: str) -> bool        |
| + grant_permission(role: str, command: str) -> None           |
| + revoke_permission(role: str, command: str) -> None          |
+---------------------------------------------------------------+
```


## Project Structure

```
discord_scheduler_bot/
│
├── botcore/
│   └── main.py
├── handlers/
│   ├── command_handler.py
│   ├── poll_manager.py
│   ├── reminder_scheduler.py
│   └── custom_command_manager.py
├── services/
│   ├── calendar_service.py
│   ├── rule_engine.py
│   └── ai_planner_agent.py
├── db/
│   ├── user_manager.py
│   ├── models.py
│   └── availability_tracker.py
├── utils/
│   ├── permissions.py
│   └── stats.py
├── config/
│   └── settings.py
└── requirements.txt
```


## Types of Relationships

- **Association:** One class uses or references another.
- **Aggregation / Composition:** One class contains another (stronger than association).
- **Dependency:** One class depends on another temporarily.
- **Inheritance:** One class derives from another (not applicable here—most are composition/association).

---

## Relationship Details

### BotCore
- **Aggregation of:**
  - CommandHandler
  - CalendarService
  - ReminderScheduler
  - UserManager
  - AIPlannerAgent
  - PollManager
  - RuleEngine
  - PermissionManager
  - StatsModule
- It owns these components and initializes/manages their lifecycle.

### CommandHandler
- **Association with** CustomCommandManager: Loads and routes custom commands.
- **Depends on** PermissionManager: For checking command-level permissions.

### UserManager
- **Composition with** UserProfile: UserManager creates/updates/deletes UserProfile records.
- **Uses** AvailabilityTracker: For tracking user activity.
- **Association with** PermissionManager: For assigning roles and privileges.

### CalendarService
- **Depends on** UserProfile: Uses user's calendar email to query Google Calendar API.
- **Association with** AvailabilityTracker: Logs availability stats.

### PollManager
- **Uses** UserManager: Verifies poll participants.
- **May depend on** StatsModule: For tracking poll engagement.

### ReminderScheduler
- **Receives jobs from:** PollManager, CommandHandler, or CalendarService.
- **Association with** UserManager: Sends reminders to users.

### AIPlannerAgent
- **Depends on** UserManager, CalendarService, and RuleEngine: Gathers context to make suggestions and resolve conflicts.

### RuleEngine
- **Depends on:** UserManager, CalendarService: Checks logical conflicts and constraints for scheduling.

### StatsModule
- **Collects data from** CommandHandler, PollManager, ReminderScheduler
- **Reports to:** Admin users or channels via BotCore.

### PermissionManager
- **Works with** UserManager and CommandHandler: Manages access control for commands.
