from app.models.user import User
from app.models.call import Call
from app.models.task import Task
from app.models.audit_log import AuditLog
from app.models.sent_email import SentEmail # ADD THIS LINE

__all__ = ["User", "Call", "Task", "AuditLog", "SentEmail"] # UPDATE THIS LINE