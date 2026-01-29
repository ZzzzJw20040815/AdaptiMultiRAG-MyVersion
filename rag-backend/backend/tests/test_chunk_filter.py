#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChunkFilterService 单元测试

测试RAG检索结果过滤服务的各种过滤规则。
"""

import pytest
from backend.service.chunk_filter import (
    ChunkFilterService,
    ChunkFilterConfig,
    DEFAULT_CHUNK_FILTER_CONFIG,
    get_chunk_filter_service
)


class MockDocument:
    """模拟文档对象"""
    def __init__(self, page_content: str, metadata: dict = None):
        self.page_content = page_content
        self.metadata = metadata or {}


# ==================== 基础功能测试 ====================

class TestChunkFilterServiceBasic:
    """基础功能测试"""
    
    def test_filter_service_initialization(self):
        """测试过滤服务初始化"""
        service = ChunkFilterService()
        assert service.config is not None
        assert service.config.enabled is True
    
    def test_filter_service_with_custom_config(self):
        """测试自定义配置"""
        config = ChunkFilterConfig(
            keyword_blacklist=["test_keyword"],
            enabled=True
        )
        service = ChunkFilterService(config)
        assert "test_keyword" in service.config.keyword_blacklist
    
    def test_empty_chunks_returns_empty(self):
        """测试空列表返回空"""
        service = ChunkFilterService()
        result = service.filter_chunks([])
        assert len(result) == 0
    
    def test_disabled_filter_returns_original(self):
        """测试禁用过滤时返回原始列表"""
        config = ChunkFilterConfig(enabled=False)
        service = ChunkFilterService(config)
        
        chunks = [MockDocument("This contains reference")]
        result = service.filter_chunks(chunks)
        assert len(result) == 1


# ==================== 关键词过滤测试 ====================

class TestKeywordFiltering:
    """关键词黑名单过滤测试"""
    
    def test_filter_acknowledgement(self):
        """测试过滤致谢章节"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("This is a valid research finding about deep learning."),
            MockDocument("We would like to acknowledge John Smith for funding."),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "deep learning" in result[0].page_content
    
    def test_filter_author_contributions(self):
        """测试过滤作者贡献声明"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("The neural network architecture consists of three layers."),
            MockDocument("Author contributions: Evaluations (ablations, designing procedures)"),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "neural network" in result[0].page_content
    
    def test_filter_latex_commands(self):
        """测试过滤LaTeX命令"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("Deep learning models show impressive results on various benchmark tasks."),
            MockDocument("\\newfloatcommand\\capbtabboxtable[][\\FBwidth] some additional content here to make it longer"),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "Deep learning" in result[0].page_content
    
    def test_filter_email_domains(self):
        """测试过滤邮箱域名"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("The experiment achieved 95% accuracy on benchmark."),
            MockDocument("Contact: researcher@google.com for more information."),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "accuracy" in result[0].page_content


# ==================== 正则过滤测试 ====================

class TestRegexFiltering:
    """正则表达式过滤测试"""
    
    def test_filter_doi_pattern(self):
        """测试过滤DOI模式"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("Results show significant improvement in accuracy on multiple benchmark datasets."),
            MockDocument("Available at doi: 10.1234/example.paper.2024 with additional content to make it longer"),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "accuracy" in result[0].page_content
    
    def test_filter_arxiv_pattern(self):
        """测试过滤arXiv模式"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("We propose a novel transformer architecture for natural language processing."),
            MockDocument("Paper available at arXiv:2404.12345 with more content to meet length requirement"),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "transformer" in result[0].page_content
    
    def test_filter_reference_citation(self):
        """测试过滤参考文献条目"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("The model achieves state-of-the-art performance on multiple evaluation benchmarks."),
            MockDocument("* Ahn et al. (2022) Michael Ahn, Anthony Brohan... arXiv preprint arXiv:2204.01691, 2022."),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "state-of-the-art" in result[0].page_content


# ==================== 长度过滤测试 ====================

class TestLengthFiltering:
    """内容长度过滤测试"""
    
    def test_filter_short_content(self):
        """测试过滤过短内容"""
        config = ChunkFilterConfig(
            keyword_blacklist=[],
            regex_patterns=[],
            min_content_length=50,
            enabled=True
        )
        service = ChunkFilterService(config)
        
        chunks = [
            MockDocument("Short"),  # 太短
            MockDocument("This is a valid document with sufficient content length for testing purposes."),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "sufficient content" in result[0].page_content


# ==================== 名单检测测试 ====================

class TestNameListFiltering:
    """纯名单检测过滤测试"""
    
    def test_filter_author_name_list(self):
        """测试过滤纯作者名单"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("The experiment demonstrates significant improvements in robotic manipulation."),
            MockDocument("Anthony Brohan Noah Brown Justice Carbajal Yevgen Chebotar Xi Chen Krzysztof Choromanski Tianli Ding Danny Driess Avinava Dubey Chelsea Finn Pete Florence Chuyuan Fu"),
        ]
        
        result = service.filter_chunks(chunks)
        assert len(result) == 1
        assert "experiment" in result[0].page_content


# ==================== 真实场景测试 ====================

class TestRealWorldScenarios:
    """真实场景过滤测试"""
    
    def test_mixed_content_filtering(self):
        """测试混合内容过滤"""
        service = ChunkFilterService()
        
        chunks = [
            # 有效正文 (长度 > 50)
            MockDocument("In this paper, we present RT-1, a transformer-based model for real-time robotic control and manipulation tasks."),
            # 参考文献 - 会被arXiv模式过滤
            MockDocument("* Ahn et al. (2022) Michael Ahn, Anthony Brohan and others. arXiv preprint arXiv:2204.01691 from 2022."),
            # 致谢 - 会被acknowledge关键词过滤
            MockDocument("We would like to acknowledge the entire research team for their valuable contributions and great support."),
            # LaTeX残留 - 会被\\newfloatcommand关键词过滤
            MockDocument("\\newfloatcommand\\correspondingauthor@google.com with additional formatting and content here."),
            # 有效正文 (长度 > 50)
            MockDocument("The results show that our model achieves 95% success rate on complex manipulation tasks in real environments."),
            # 纯作者名单 - 会被人名检测过滤
            MockDocument("John Smith Alice Johnson Bob Williams Carol Davis Eve Wilson Frank Miller Grace Lee Henry Chen Isabella Zhang"),
        ]
        
        result = service.filter_chunks(chunks)
        
        # 应该保留至少1个有效正文
        assert len(result) >= 1
        # 验证有正确的有效内容被保留
        valid_found = any("RT-1" in doc.page_content or "95% success rate" in doc.page_content for doc in result)
        assert valid_found


# ==================== 统计功能测试 ====================

class TestFilterStats:
    """过滤统计功能测试"""
    
    def test_get_filter_stats(self):
        """测试获取过滤统计信息"""
        service = ChunkFilterService()
        
        chunks = [
            MockDocument("Valid content with sufficient length for testing purposes in our system."),
            MockDocument("Short text"),  # 过短
            MockDocument("We would like to acknowledge the team for their great support and help."),
        ]
        
        stats = service.get_filter_stats(chunks)
        
        assert stats["total_chunks"] == 3
        # 至少1个被过滤（acknowledge关键词或短内容）
        total_filtered = sum(stats["would_filter"].values())
        assert total_filtered >= 1
        assert stats["would_retain"] >= 1


# ==================== 全局单例测试 ====================

class TestGlobalSingleton:
    """全局单例测试"""
    
    def test_get_chunk_filter_service(self):
        """测试获取全局单例"""
        service1 = get_chunk_filter_service()
        service2 = get_chunk_filter_service()
        
        assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
