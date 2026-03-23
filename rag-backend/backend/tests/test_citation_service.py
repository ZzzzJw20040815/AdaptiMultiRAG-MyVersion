#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""citation_service 单元测试"""

from backend.service.citation_service import normalize_citation_index_section


def test_normalize_citation_index_section_rewrites_reference_heading():
    answer = """这是正文内容。\n\n**参考文献：**\n[S1] 文献A\n[S2] 文献A"""

    normalized = normalize_citation_index_section(answer)

    assert "**引用片段索引：**" in normalized
    assert "参考文献" not in normalized


def test_normalize_citation_index_section_handles_plain_heading():
    answer = """正文\n参考文献：\n[S1] 文献A"""

    normalized = normalize_citation_index_section(answer)

    assert "引用片段索引：" in normalized
    assert "参考文献：" not in normalized