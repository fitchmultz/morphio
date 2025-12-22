"""Template service exceptions."""

from app.utils.error_handlers import ApplicationException


class DefaultTemplateEditException(ApplicationException):
    """Exception raised when attempting to edit a default template."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class DuplicateTemplateNameException(ApplicationException):
    """Exception raised when a template with the same name already exists."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message, status_code)


class TemplateNotFoundException(ApplicationException):
    """Exception raised when a template is not found."""

    def __init__(self, message: str, status_code: int = 404):
        super().__init__(message, status_code)


class TemplateNotOwnedException(ApplicationException):
    """Exception raised when a user tries to access a template they don't own."""

    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message, status_code)
