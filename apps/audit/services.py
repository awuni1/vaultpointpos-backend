"""AuditService — call from views after significant changes."""


def log(action, entity_type='', entity_id='', user=None, before=None, after=None, ip='', user_agent=''):
    from .models import AuditLog
    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_value=before,
        after_value=after,
        ip_address=ip,
        user_agent=user_agent,
    )
