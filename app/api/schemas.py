# app/api/schemas.py
"""
API 请求/响应数据模型
"""
from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class HeaderModel(BaseModel):
    """请求头模型"""
    request_id: str


class TestcaseModel(BaseModel):
    """测试用例模型"""
    number: str
    scheduleBlockId: str
    exeplatform: str
    name: str
    svnScriptPath: str


class JobParamModel(BaseModel):
    """任务参数模型"""
    teps: List[str] = []
    tepType: str = ""
    groupId: str = ""
    taskProjectName: str = ""
    userExtendContent: str = "{}"
    taskType: str = "4"
    testcaseBlockID: str = ""
    taskProjectID: str = ""
    taskID: str = ""
    runRound: str = "1"
    exeplatform: str = "PyTestAgent"
    schedulerBlockID: str = ""
    tcBlockCount: str = "1"
    testcase: List[TestcaseModel] = []


class SendJobRequest(BaseModel):
    """sendJob 请求模型"""
    header: HeaderModel
    param: Dict[str, Any]  # 包含 param 字段


class StopJobParam(BaseModel):
    """stopJob 参数模型"""
    groupId: str
    taskID: str
    schedulerID: str
    tcBlockID: str
    tepUrl: str = ""
    netWork: str = "green"
    envId: str = ""
    option: str = ""
    stopTimeOut: str = "300"
    stopType: str = "later"


class StopJobRequest(BaseModel):
    """stopJob 请求模型"""
    param: StopJobParam


class CloseJobParam(BaseModel):
    """closeJob 参数模型"""
    groupId: str
    taskID: str
    schedulerID: str
    tcBlockID: str


class CloseJobRequest(BaseModel):
    """closeJob 请求模型"""
    param: CloseJobParam


class ResponseParam(BaseModel):
    """响应参数模型"""
    status: str = "ok"
    result: str = ""


class ResponseHeader(BaseModel):
    """响应头模型"""
    request_id: str


class ApiResponse(BaseModel):
    """API 响应模型"""
    param: ResponseParam
    header: ResponseHeader