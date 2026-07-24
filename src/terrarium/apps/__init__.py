"""Five simulated application modules."""

from .calendar import CalendarApp
from .chat import ChatApp
from .crm import CrmApp
from .email import EmailApp
from .files import FilesApp

__all__ = ["EmailApp", "CalendarApp", "FilesApp", "ChatApp", "CrmApp"]

