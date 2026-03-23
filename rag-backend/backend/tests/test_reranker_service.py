#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RerankerService 单元测试
"""

from backend.service.reranker_service import RerankerService, RerankerConfig


class MockDoc:
    def __init__(self, text: str):
        self.page_content = text
        self.metadata = {}


def test_local_fallback_demotes_title_metadata_when_api_fails(monkeypatch):
    service = RerankerService(
        RerankerConfig(model="qwen3-rerank", threshold=0.3, top_k=5, enabled=True)
    )

    def _raise_api_error(*args, **kwargs):
        raise RuntimeError("api unavailable")

    # 强制触发 API 失败 -> 走本地兜底逻辑
    monkeypatch.setattr("backend.service.reranker_service.TextReRank.call", _raise_api_error)

    docs = [
        MockDoc(
            "3D-VLA: A 3D Vision-Language-Action Generative World Model"
            "Haoyu Zhen1 2Xiaowen Qiu1Peihao Chen3 https://vis-www.cs. umass. edu/3dvla"
            "AbstractRecent vision-language-action (VLA) models rely on 2D inputs."
        ),
        MockDoc(
            "Another challenge for building such a generative world model is to integrate "
            "3D perception, reasoning and action planning for embodied tasks."
        ),
    ]

    result = service.rerank(
        query="3D-VLA这篇文献的主要内容是什么",
        documents=docs,
        top_k=2,
        threshold=0.0
    )

    assert len(result) == 2
    # 期望正文片段排在标题页元数据前
    assert "Another challenge for building" in result[0].page_content
    assert result[0].metadata.get("rerank_fallback") is True
