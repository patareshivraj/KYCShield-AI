class KYCShieldException(Exception):
    def __init__(self, error_code: str, message: str, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(KYCShieldException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("VALIDATION_ERROR", message, details)

class UnsupportedFormatError(KYCShieldException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("UNSUPPORTED_FORMAT", message, details)

class JobNotFoundError(KYCShieldException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("JOB_NOT_FOUND", message, details)

class PipelineFailedError(KYCShieldException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("PIPELINE_FAILED", message, details)
