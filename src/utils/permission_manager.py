from ..database.models import UserProfile

class PermissionManager:
    """Manages user permissions and roles."""

    def __init__(self):
        self.role_permissions = {}
        self.owner_id = None

    def set_owner(self, owner_id: int):
        self.owner_id = owner_id

    def can_execute(self, user: UserProfile, command: str) -> bool:
        if self.owner_id is not None and user.discord_id == self.owner_id:
            return True
        for role in user.roles:
            if command in self.role_permissions.get(role, []):
                return True
        return False

    def grant_permission(self, role: str, command: str) -> None:
        if role not in self.role_permissions:
            self.role_permissions[role] = []
        if command not in self.role_permissions[role]:
            self.role_permissions[role].append(command)

    def revoke_permission(self, role: str, command: str) -> bool:
        if role in self.role_permissions and command in self.role_permissions[role]:
            self.role_permissions[role].remove(command)
            return True
        return False

    def add_role(self, role: str, commands: list = None):
        if role not in self.role_permissions:
            self.role_permissions[role] = commands or []

    def remove_role(self, role: str):
        """Remove a role and all its permissions"""
        if role in self.role_permissions:
            del self.role_permissions[role]

    def get_role_permissions(self, role: str) -> list:
        """Get all permissions for a specific role"""
        return self.role_permissions.get(role, [])

    def get_all_roles(self) -> list:
        """Get all roles"""
        return list(self.role_permissions.keys())

    def add_user_to_role(self, user: UserProfile, role: str):
        if role not in user.roles:
            user.roles.append(role)
