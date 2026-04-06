# app/git_ops/repo_manager.py
"""
Git 仓库操作模块
- clone 仓库
- pull 更新
- 分支切换（强制还原本地修改）
"""
import subprocess
import json
from pathlib import Path
from typing import Tuple, Optional
from urllib.parse import urlparse
from app.config import config
from app.utils.logger import logger


class RepoManager:
    """Git 仓库管理器"""

    def __init__(self):
        self.work_dir = Path(config.git_work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _run_git_command(self, cmd: list, cwd: Optional[Path] = None) -> Tuple[bool, str]:
        """执行 Git 命令"""
        # 在所有 git 命令前添加忽略证书验证的配置
        if cmd[0] == 'git':
            cmd = ['git', '-c', 'http.sslVerify=false'] + cmd[1:]
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                logger.error(f"Git 命令失败: {cmd}, 错误: {result.stderr}")
                return False, result.stderr
            return True, result.stdout
        except subprocess.TimeoutExpired:
            logger.error(f"Git 命令超时: {cmd}")
            return False, "timeout"
        except Exception as e:
            logger.error(f"Git 命令异常: {cmd}, 错误: {e}")
            return False, str(e)

    def _parse_repo_name(self, git_url: str) -> str:
        """从 git_url 解析仓库名"""
        # 处理 HTTPS URL
        if git_url.startswith('https://') or git_url.startswith('http://'):
            parsed = urlparse(git_url)
            path = parsed.path.rstrip('/')
            # 移除 .git 后缀
            if path.endswith('.git'):
                path = path[:-4]
            # 获取最后一部分作为仓库名
            return path.split('/')[-1]

        # 处理 SSH URL
        if git_url.startswith('git@'):
            path = git_url.split(':')[-1]
            if path.endswith('.git'):
                path = path[:-4]
            return path.split('/')[-1]

        # 默认处理
        return git_url.split('/')[-1].replace('.git', '')

    def prepare_repo(
        self,
        git_url: str,
        user_extend_content: str
    ) -> Tuple[bool, Path, str]:
        """
        准备 Git 仓库
        返回: (成功标志, 仓库路径, 错误信息)
        """
        repo_name = self._parse_repo_name(git_url)
        repo_path = self.work_dir / repo_name

        logger.info(f"准备仓库: {git_url}, 目标路径: {repo_path}")

        # 解析 exeParam 获取分支
        branch = config.git_default_branch
        try:
            extend_data = json.loads(user_extend_content)
            exe_param_str = extend_data.get('exeParam', '{}')
            exe_param = json.loads(exe_param_str)
            branch = exe_param.get('branch', config.git_default_branch)
        except Exception as e:
            logger.warning(f"解析 exeParam 失败: {e}, 使用默认分支")

        logger.info(f"目标分支: {branch}")

        # 检查仓库是否存在
        if not repo_path.exists():
            # Clone 仓库
            logger.info(f"仓库不存在，开始 clone: {git_url}")
            success, output = self._run_git_command(
                ['git', 'clone', git_url, str(repo_path)]
            )
            if not success:
                return False, repo_path, f"clone 失败: {output}"
        else:
            logger.info(f"仓库已存在: {repo_path}")

        # 进入仓库目录
        git_dir = repo_path / '.git'
        if not git_dir.exists():
            return False, repo_path, "仓库目录无效"

        # 获取当前分支
        success, current_branch = self._run_git_command(
            ['git', 'branch', '--show-current'],
            cwd=repo_path
        )
        if success:
            current_branch = current_branch.strip()
            logger.info(f"当前分支: {current_branch}")

        # 检查是否需要切换分支
        if current_branch != branch:
            logger.info(f"切换分支: {current_branch} -> {branch}")

            # 强制还原本地修改
            success, _ = self._run_git_command(
                ['git', 'checkout', '--', '.'],
                cwd=repo_path
            )
            if not success:
                logger.warning("还原本地修改失败（可能没有修改）")

            # 切换分支
            success, output = self._run_git_command(
                ['git', 'checkout', branch],
                cwd=repo_path
            )
            if not success:
                # 尝试 fetch 后再切换
                self._run_git_command(['git', 'fetch'], cwd=repo_path)
                success, output = self._run_git_command(
                    ['git', 'checkout', branch],
                    cwd=repo_path
                )
                if not success:
                    return False, repo_path, f"切换分支失败: {output}"

        # Pull 更新
        logger.info("执行 git pull")
        success, output = self._run_git_command(
            ['git', 'pull'],
            cwd=repo_path
        )
        if not success:
            logger.warning(f"pull 失败: {output}")
            # 不影响继续执行，可能已经是最新的

        logger.info(f"仓库准备完成: {repo_path}")
        return True, repo_path, ""


# 全局仓库管理器实例
repo_manager = RepoManager()