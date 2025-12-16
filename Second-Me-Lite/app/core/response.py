from typing import Any, Optional
from fastapi.responses import JSONResponse


class APIResponse:
    """统一 API 响应格式"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        code: int = 200
    ) -> JSONResponse:
        """
        成功响应
        
        Args:
            data: 响应数据
            message: 响应消息
            code: HTTP 状态码
            
        Returns:
            JSONResponse 对象
        """
        response_data = {
            "code": code,
            "message": message,
            "data": data
        }
        return JSONResponse(status_code=code, content=response_data)
    
    @staticmethod
    def error(
        code: int = 500,
        message: str = "Internal server error",
        data: Any = None
    ) -> JSONResponse:
        """
        错误响应
        
        Args:
            code: HTTP 状态码
            message: 错误消息
            data: 可选的错误详情数据
            
        Returns:
            JSONResponse 对象
        """
        response_data = {
            "code": code,
            "message": message,
            "data": data
        }
        return JSONResponse(status_code=code, content=response_data)

