"""
Decorators for command validation and permission checking.
Uses Decorator pattern to add functionality to commands.
"""

from functools import wraps
from typing import Dict, Any, Callable, Awaitable
from .base_command import PermissionLevel
from .validators import BaseValidator, ValidationError

def requires_permission(level: PermissionLevel):
    """
    Decorator to set permission level for a command.
    Usage:
        @requires_permission(PermissionLevel.ADMIN)
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        # Set the permission level on the class
        command_class._permission_level = level

        # Modify the constructor to use this permission level
        original_init = command_class.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            # Override permission_level if not explicitly set
            if 'permission_level' not in kwargs:
                kwargs['permission_level'] = level
            original_init(self, *args, **kwargs)

        command_class.__init__ = new_init
        return command_class
    return decorator

def validate_input(**validators: Dict[str, Callable[[Any], Awaitable[Any]]]):
    """
    Decorator to add input validation to commands.
    Usage:
        @validate_input(
            calendar_name=async_validate_calendar_name,
            start_time=async_validate_future_datetime
        )
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        original_validate = command_class.validate_input

        @wraps(original_validate)
        async def new_validate(self, interaction, **kwargs):
            errors = []
            validated_data = {}

            # Run the original validation first
            original_result = await original_validate(self, interaction, **kwargs)
            if not original_result.get('valid', True):
                errors.extend(original_result.get('errors', []))
            else:
                validated_data.update(original_result.get('data', {}))

            # Run decorator validations
            for field_name, validator_func in validators.items():
                if field_name in kwargs:
                    try:
                        validated_value = await validator_func(kwargs[field_name])
                        validated_data[field_name] = validated_value
                    except ValidationError as e:
                        errors.append(f"{field_name}: {str(e)}")
                    except Exception as e:
                        errors.append(f"{field_name}: Validation error - {str(e)}")

            if errors:
                return {'valid': False, 'errors': errors}

            return {'valid': True, 'data': validated_data}

        command_class.validate_input = new_validate
        return command_class
    return decorator

def log_command_usage(logger_name: str = "commands"):
    """
    Decorator to log command usage.
    Usage:
        @log_command_usage("my_commands")
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        original_execute = command_class.execute

        @wraps(original_execute)
        async def new_execute(self, interaction, **kwargs):
            import logging
            logger = logging.getLogger(logger_name)

            user_info = f"{interaction.user.name}#{interaction.user.discriminator} ({interaction.user.id})"
            guild_info = f"Guild: {interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "DM"

            logger.info(f"Command {self.command_name} executed by {user_info} in {guild_info}")

            try:
                result = await original_execute(self, interaction, **kwargs)
                logger.info(f"Command {self.command_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"Command {self.command_name} failed: {str(e)}")
                raise

        command_class.execute = new_execute
        return command_class
    return decorator

def rate_limit(calls_per_minute: int = 10, per_user: bool = True):
    """
    Decorator to add rate limiting to commands.
    Usage:
        @rate_limit(calls_per_minute=5, per_user=True)
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        from collections import defaultdict
        from datetime import datetime, timedelta

        # Storage for rate limit tracking
        if not hasattr(command_class, '_rate_limits'):
            command_class._rate_limits = defaultdict(list)

        original_execute = command_class.execute

        @wraps(original_execute)
        async def new_execute(self, interaction, **kwargs):
            now = datetime.utcnow()
            cutoff = now - timedelta(minutes=1)

            # Determine the key for rate limiting
            if per_user:
                key = f"{interaction.user.id}:{self.command_name}"
            else:
                key = f"global:{self.command_name}"

            # Clean old entries
            command_class._rate_limits[key] = [
                timestamp for timestamp in command_class._rate_limits[key]
                if timestamp > cutoff
            ]

            # Check rate limit
            if len(command_class._rate_limits[key]) >= calls_per_minute:
                from .builders import EmbedBuilder
                embed = EmbedBuilder().warning(
                    "Rate Limited",
                    f"You can only use this command {calls_per_minute} times per minute. Please wait and try again."
                ).build()
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            # Record this call
            command_class._rate_limits[key].append(now)

            return await original_execute(self, interaction, **kwargs)

        command_class.execute = new_execute
        return command_class
    return decorator

def ephemeral_response(ephemeral: bool = True):
    """
    Decorator to make command responses ephemeral by default.
    Usage:
        @ephemeral_response()
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        original_init = command_class.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            if 'ephemeral' not in kwargs:
                kwargs['ephemeral'] = ephemeral
            original_init(self, *args, **kwargs)

        command_class.__init__ = new_init
        return command_class
    return decorator

def cache_result(duration_minutes: int = 5, per_user: bool = True):
    """
    Decorator to cache command results.
    Usage:
        @cache_result(duration_minutes=10, per_user=True)
        class MyCommand(BaseCommand):
            pass
    """
    def decorator(command_class):
        from datetime import datetime, timedelta

        if not hasattr(command_class, '_cache'):
            command_class._cache = {}

        original_process = command_class.process_command

        @wraps(original_process)
        async def new_process(self, interaction, data):
            now = datetime.utcnow()

            # Create cache key
            if per_user:
                cache_key = f"{interaction.user.id}:{self.command_name}:{hash(str(sorted(data.items())))}"
            else:
                cache_key = f"global:{self.command_name}:{hash(str(sorted(data.items())))}"

            # Check cache
            if cache_key in command_class._cache:
                cached_result, cached_time = command_class._cache[cache_key]
                if now - cached_time < timedelta(minutes=duration_minutes):
                    return cached_result

            # Execute and cache result
            result = await original_process(self, interaction, data)
            command_class._cache[cache_key] = (result, now)

            # Clean old cache entries periodically
            if len(command_class._cache) > 100:  # Simple cleanup
                cutoff = now - timedelta(minutes=duration_minutes)
                command_class._cache = {
                    k: v for k, v in command_class._cache.items()
                    if v[1] > cutoff
                }

            return result

        command_class.process_command = new_process
        return command_class
    return decorator