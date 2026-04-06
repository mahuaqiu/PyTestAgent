# app/api/schemas.py
"""
API 请求/响应数据模型
- 所有字段设为可选，适配调度中心的实际参数
- 允许额外字段，避免字段名差异导致验证失败
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class HeaderModel(BaseModel):
    """请求头模型"""
    model_config = {"extra": "allow"}  # 允许额外字段

    request_id: str = Field(default="")


class TestcaseModel(BaseModel):
    """测试用例模型"""
    model_config = {"extra": "allow"}  # 允许额外字段

    number: str = Field(default="")
    scheduleBlockId: str = Field(default="")
    exeplatform: str = Field(default="PyTestAgent")
    name: str = Field(default="")
    svnScriptPath: str = Field(default="")


class JobParamModel(BaseModel):
    """任务参数模型"""
    model_config = {"extra": "allow"}  # 允许额外字段

    teps: List[str] = Field(default_factory=list)
    tepType: str = Field(default="")
    groupId: str = Field(default="")
    taskProjectName: str = Field(default="")
    userExtendContent: str = Field(default="{}")
    taskType: str = Field(default="4")
    testcaseBlockID: str = Field(default="")
    taskProjectID: str = Field(default="")
    taskID: str = Field(default="")
    runRound: str = Field(default="1")
    exeplatform: str = Field(default="PyTestAgent")
    schedulerBlockID: str = Field(default="")
    tcBlockCount: str = Field(default="1")
    testcase: List[TestcaseModel] = Field(default_factory=list)


class SendJobRequest(BaseModel):
    """sendJob 请求模型"""
    model_config = {"extra": "allow"}  # 允许额外字段

    header: Optional[HeaderModel] = Field(default=None)
    param: Optional[JobParamModel] = Field(default=None)


class StopJobParam(BaseModel):
    """stopJob 参数模型"""
    model_config = {"extra": "allow"}

    groupId: str = Field(default="")
    taskID: str = Field(default="")
    schedulerID: str = Field(default="")
    tcBlockID: str = Field(default="")
    tepUrl: str = Field(default="")
    netWork: str = Field(default="green")
    envId: str = Field(default="")
    option: str = Field(default="")
    stopTimeOut: str = Field(default="300")
    stopType: str = Field(default="later")


class StopJobRequest(BaseModel):
    """stopJob 请求模型"""
    model_config = {"extra": "allow"}

    param: Optional[StopJobParam] = Field(default=None)


class CloseJobParam(BaseModel):
    """closeJob 参数模型"""
    model_config = {"extra": "allow"}

    groupId: str = Field(default="")
    taskID: str = Field(default="")
    schedulerID: str = Field(default="")
    tcBlockID: str = Field(default="")


class CloseJobRequest(BaseModel):
    """closeJob 请求模型"""
    model_config = {"extra": "allow"}

    param: Optional[CloseJobParam] = Field(default=None)


class ResponseParam(BaseModel):
    """响应参数模型"""
    status: str = "ok"
    result: str = ""


class ResponseHeader(BaseModel):
    """响应头模型"""
    request_id: str = ""


class ApiResponse(BaseModel):
    """API 响应模型"""
    param: ResponseParam
    header: ResponseHeader