# app/config.py
"""
配置管理模块
- 从 config.yaml 加载默认配置
- 支持环境变量覆盖（使用 __ 分隔嵌套层级）
"""
import os
import yaml
from pathlib import Path
from typing import Any, Optional


class Config:
    """配置管理类"""

    _instance: Optional['Config'] = None
    _config_data: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f) or {}
        else:
            self._config_data = {}

    def _get_env_key(self, keys: list) -> str:
        """生成环境变量键名"""
        return '__'.join(k.upper() for k in keys)

    def _get_value(self, keys: list) -> Any:
        """递归获取配置值，环境变量优先"""
        env_key = self._get_env_key(keys)
        env_value = os.getenv(env_key)

        if env_value is not None:
            # 尝试转换类型
            try:
                if env_value.isdigit():
                    return int(env_value)
                return env_value
            except:
                return env_value

        # 从 config.yaml 获取
        value = self._config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value

    @property
    def agent_ip(self) -> str:
        return self._get_value(['agent', 'ip']) or '127.0.0.1'

    @property
    def agent_port(self) -> int:
        return self._get_value(['agent', 'port']) or 5000

    @property
    def agent_version(self) -> str:
        return self._get_value(['agent', 'version']) or '1.0'

    @property
    def agent_author(self) -> str:
        return self._get_value(['agent', 'author']) or 'unknown'

    @property
    def scheduler_base_url(self) -> str:
        return self._get_value(['scheduler', 'base_url']) or ''

    @property
    def test_platform_base_url(self) -> str:
        return self._get_value(['test_platform', 'base_url']) or ''

    @property
    def git_work_dir(self) -> str:
        return self._get_value(['git', 'work_dir']) or '/home'

    @property
    def git_default_branch(self) -> str:
        return self._get_value(['git', 'default_branch']) or 'master'

    @property
    def max_parallel(self) -> int:
        return self._get_value(['execution', 'max_parallel']) or 3

    @property
    def testcase_timeout(self) -> int:
        """单个用例超时时间（秒），默认1小时"""
        return self._get_value(['execution', 'testcase_timeout']) or 3600

    @property
    def rg_id(self) -> str:
        return self._get_value(['registration', 'rg_id']) or ''

    @property
    def product_id(self) -> str:
        return self._get_value(['registration', 'product_id']) or ''

    @property
    def heartbeat_interval(self) -> int:
        return self._get_value(['heartbeat', 'interval']) or 120

    @property
    def report_cleanup_interval(self) -> int:
        return self._get_value(['report_cleanup', 'interval']) or 86400

    @property
    def report_retention_days(self) -> int:
        return self._get_value(['report_cleanup', 'retention_days']) or 7

    @property
    def agent_url(self) -> str:
        return f"http://{self.agent_ip}:{self.agent_port}"

    @property
    def agent_group_id(self) -> str:
        return f"{self.agent_ip}:{self.agent_port}"


# 全局配置实例
config = Config()