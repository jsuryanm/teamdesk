class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message 

class AuthenticationError(DomainError):
    status_code = 401 
    code = "authentication_failed"

class PermissionDeniedError(DomainError):
    status_code = 403
    code = "permission_denied"


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"
