from .models import Project, StepInstance, User


def can_view_project(project: Project, user: User) -> bool:
    if user.role == "admin" or project.created_by == user.id:
        return True
    return user.id in {a.assignee_id for a in project.assignments} | {a.user_id for a in project.approver_assignments}


def can_view_instance(inst: StepInstance, user: User) -> bool:
    if user.role == "admin" or inst.assignee_id == user.id or inst.project.created_by == user.id:
        return True
    if any(a.user_id == user.id for a in inst.approvals):
        return True
    return any(a.user_id == user.id and a.step_id == inst.step_id for a in inst.project.approver_assignments)
