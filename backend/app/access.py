from .models import Project, User


def can_view_project(project: Project, user: User) -> bool:
    return (user.role == "admin" or project.created_by == user.id
            or any(m.user_id == user.id for m in project.members))


def can_manage_project(project: Project, user: User) -> bool:
    return user.role == "admin" or project.created_by == user.id
