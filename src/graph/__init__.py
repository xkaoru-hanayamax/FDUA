"""
LangGraphベースの提案書生成エージェントシステム

直線フローで財務・有報データから提案書を自動生成
"""

from .proposal_agent import create_proposal_agent, run_proposal_agent

__all__ = ["create_proposal_agent", "run_proposal_agent"]
