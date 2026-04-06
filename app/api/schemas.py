# app/api/schemas.py
"""
API 请求/响应数据模型
- 完全宽松模式，不限制字段类型
- 适配调度中心的实际参数格式
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional


class HeaderModel(BaseModel):
    """请求头模型"""
    model_config = {"extra": "allow"}

    requestID: Optional[str] = None  # 调度中心使用 requestID
    request_id: Optional[str] = None  # 兼容其他可能的命名


class SendJobRequest(BaseModel):
    """sendJob 请求模型 - 完全宽松"""
    model_config = {"extra": "allow"}

    header: Optional[Dict[str, Any]] = None
    param: Optional[Dict[str, Any]] = None


class StopJobRequest(BaseModel):
    """stopJob 请求模型 - 完全宽松"""
    model_config = {"extra": "allow"}

    header: Optional[Dict[str, Any]] = None
    param: Optional[Dict[str, Any]] = None


class CloseJobRequest(BaseModel):
    """closeJob 请求模型 - 完全宽松"""
    model_config = {"extra": "allow"}

    header: Optional[Dict[str, Any]] = None
    param: Optional[Dict[str, Any]] = None


class ResponseParam(BaseModel):
    """响应参数模型"""
    status: str = "ok"
    result: str = ""


class ResponseHeader(BaseModel):
    """响应头模型"""
    model_config = {"extra": "allow"}

    requestID: Optional[str] = None
    request_id: Optional[str] = None


class ApiResponse(BaseModel):
    """API 响应模型"""
    param: ResponseParam
    header: Optional[Dict[str, Any]] = None