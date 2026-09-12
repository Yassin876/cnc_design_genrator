from fastapi import HTTPException

class AuthException(HTTPException):
    def __init__(self, status_code: int, message: str, code: str):
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "message": message,
                "code": code
            }
        )
