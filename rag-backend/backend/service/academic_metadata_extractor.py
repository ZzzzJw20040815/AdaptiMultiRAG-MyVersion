#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术元数据提取器服务 (PR-6)

使用 LLM 从 PDF 文本中提取学术论文元数据:
- 标题 (paper_title)
- 作者 (authors)
- 机构 (affiliations)
- 摘要 (abstract)
- 关键词 (keywords)
- DOI
- 发表年份 (publication_year)
- 发表期刊/会议 (publication_venue)
- 参考文献数量 (references_count)
"""

import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class AcademicMetadata:
    """学术论文元数据"""
    paper_title: Optional[str] = None
    authors: Optional[List[str]] = None
    affiliations: Optional[List[str]] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    doi: Optional[str] = None
    publication_year: Optional[int] = None
    publication_venue: Optional[str] = None
    references_count: Optional[int] = None
    
    # 提取置信度
    confidence_score: Optional[float] = None
    extraction_method: str = "llm"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，过滤 None 值"""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def is_valid(self) -> bool:
        """检查是否提取到有效的元数据"""
        return bool(self.paper_title or self.authors or self.abstract)


# 学术元数据提取 Prompt
ACADEMIC_METADATA_EXTRACTION_PROMPT = """你是一个专业的学术论文元数据提取助手。请从以下论文文本中提取元数据信息。

## 待提取的字段

1. **paper_title** - 论文标题（完整的标题，包括副标题）
2. **authors** - 作者列表（JSON 数组格式，如 ["张三", "李四"]）
3. **affiliations** - 作者机构/单位（JSON 数组格式）
4. **abstract** - 摘要（完整的摘要文本）
5. **keywords** - 关键词（JSON 数组格式）
6. **doi** - DOI 编号（如果有）
7. **publication_year** - 发表年份（4位数字）
8. **publication_venue** - 发表期刊/会议名称
9. **references_count** - 参考文献数量（估计值）

## 输出格式

请以 JSON 格式返回提取结果，例如：
```json
{
  "paper_title": "论文标题",
  "authors": ["作者1", "作者2"],
  "affiliations": ["单位1", "单位2"],
  "abstract": "摘要文本...",
  "keywords": ["关键词1", "关键词2"],
  "doi": "10.xxxx/xxxxx",
  "publication_year": 2024,
  "publication_venue": "期刊名称",
  "references_count": 30,
  "confidence_score": 0.9
}
```

## 注意事项

1. 如果某个字段在文本中未找到，请设置为 null
2. confidence_score 表示你对提取结果的置信度（0-1）
3. 只返回 JSON，不要添加其他解释文字
4. 确保 JSON 格式正确

## 论文文本（前 8000 字符）

{text}
"""


async def extract_metadata_with_llm(
    text: str,
    chat_model = None,
    max_text_length: int = 8000
) -> AcademicMetadata:
    """
    使用 LLM 从文本中提取学术元数据
    
    Args:
        text: 论文文本（通常是 PDF 提取的前几页）
        chat_model: LangChain 聊天模型实例
        max_text_length: 最大文本长度
        
    Returns:
        AcademicMetadata: 提取的元数据
    """
    if not text or len(text.strip()) < 100:
        logger.warning("文本太短，无法提取元数据")
        return AcademicMetadata()
    
    # 截取文本以控制 Token 消耗
    truncated_text = text[:max_text_length]
    
    # 如果没有提供 chat_model，尝试加载
    if chat_model is None:
        try:
            from backend.config.models import initialize_chat_model
            chat_model = initialize_chat_model()
        except Exception as e:
            logger.error(f"加载聊天模型失败: {e}")
            return AcademicMetadata()
    
    try:
        # 构建 prompt
        prompt = ACADEMIC_METADATA_EXTRACTION_PROMPT.format(text=truncated_text)
        
        # 调用 LLM
        logger.info("调用 LLM 提取学术元数据...")
        response = await chat_model.ainvoke(prompt)
        
        # 提取响应内容
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        # 解析 JSON
        metadata = _parse_llm_response(response_text)
        metadata.extraction_method = "llm"
        
        logger.info(f"LLM 元数据提取成功: {metadata.paper_title or '未知标题'}")
        return metadata
        
    except Exception as e:
        logger.error(f"LLM 元数据提取失败: {e}")
        return AcademicMetadata()


def _parse_llm_response(response_text: str) -> AcademicMetadata:
    """
    解析 LLM 响应，提取 JSON 格式的元数据
    
    Args:
        response_text: LLM 响应文本
        
    Returns:
        AcademicMetadata: 解析的元数据
    """
    try:
        # 尝试直接解析 JSON
        data = json.loads(response_text.strip())
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON 块
        json_match = re.search(r'```json\s*\n?(.*?)\n?```', response_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                logger.warning("无法解析 LLM 响应中的 JSON")
                return AcademicMetadata()
        else:
            # 尝试找到 { } 包围的 JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.warning("无法解析 LLM 响应")
                    return AcademicMetadata()
            else:
                return AcademicMetadata()
    
    # 构建 AcademicMetadata 对象
    return AcademicMetadata(
        paper_title=data.get('paper_title'),
        authors=data.get('authors') if isinstance(data.get('authors'), list) else None,
        affiliations=data.get('affiliations') if isinstance(data.get('affiliations'), list) else None,
        abstract=data.get('abstract'),
        keywords=data.get('keywords') if isinstance(data.get('keywords'), list) else None,
        doi=data.get('doi'),
        publication_year=int(data['publication_year']) if data.get('publication_year') else None,
        publication_venue=data.get('publication_venue'),
        references_count=int(data['references_count']) if data.get('references_count') else None,
        confidence_score=float(data['confidence_score']) if data.get('confidence_score') else None,
    )


def extract_metadata_from_text_heuristic(text: str) -> AcademicMetadata:
    """
    使用启发式规则从文本中提取元数据（作为 LLM 的备用方案）
    
    Args:
        text: 论文文本
        
    Returns:
        AcademicMetadata: 提取的元数据
    """
    metadata = AcademicMetadata(extraction_method="heuristic")
    
    if not text:
        return metadata
    
    # 提取 DOI
    doi_match = re.search(r'10\.\d{4,}/[^\s]+', text)
    if doi_match:
        metadata.doi = doi_match.group(0).rstrip('.,;)')
    
    # 提取年份
    year_matches = re.findall(r'\b(19|20)\d{2}\b', text[:2000])
    if year_matches:
        # 优先取最近的年份
        years = sorted(set(int(y) for y in year_matches), reverse=True)
        for year in years:
            if 1990 <= year <= 2030:
                metadata.publication_year = year
                break
    
    # 提取摘要 (尝试多种模式)
    abstract_patterns = [
        r'(?:Abstract|ABSTRACT|摘要)[:\s]*\n?(.*?)(?:\n\n|Keywords|KEYWORDS|关键词|Introduction|INTRODUCTION|1\.|1\s)',
        r'(?:Summary|SUMMARY)[:\s]*\n?(.*?)(?:\n\n|Keywords|Introduction)',
    ]
    
    for pattern in abstract_patterns:
        abstract_match = re.search(pattern, text[:5000], re.DOTALL | re.IGNORECASE)
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            if len(abstract) > 50:  # 确保摘要足够长
                metadata.abstract = abstract[:2000]  # 限制长度
                break
    
    # 提取关键词
    keywords_patterns = [
        r'(?:Keywords|KEYWORDS|关键词)[:\s]*\n?(.*?)(?:\n\n|Introduction|INTRODUCTION|1\.|$)',
    ]
    
    for pattern in keywords_patterns:
        kw_match = re.search(pattern, text[:3000], re.DOTALL | re.IGNORECASE)
        if kw_match:
            kw_text = kw_match.group(1).strip()
            # 尝试按逗号、分号或换行分割
            keywords = re.split(r'[;,;\n·•]', kw_text)
            keywords = [k.strip() for k in keywords if k.strip() and len(k.strip()) < 50]
            if keywords:
                metadata.keywords = keywords[:10]  # 最多 10 个关键词
                break
    
    # 估计参考文献数量
    ref_patterns = [
        r'\[(\d+)\]',  # [1], [2], ...
        r'^\[\d+\]',   # 行首引用
    ]
    
    for pattern in ref_patterns:
        refs = re.findall(pattern, text, re.MULTILINE)
        if refs:
            try:
                max_ref = max(int(r) for r in refs if r.isdigit())
                if max_ref < 500:  # 合理范围
                    metadata.references_count = max_ref
                    break
            except ValueError:
                pass
    
    metadata.confidence_score = 0.5  # 启发式方法置信度较低
    
    return metadata


async def extract_academic_metadata(
    text: str,
    use_llm: bool = True,
    chat_model = None
) -> AcademicMetadata:
    """
    提取学术元数据（主入口函数）
    
    优先使用 LLM，失败时回退到启发式方法
    
    Args:
        text: 论文文本
        use_llm: 是否使用 LLM
        chat_model: LangChain 聊天模型
        
    Returns:
        AcademicMetadata: 提取的元数据
    """
    metadata = AcademicMetadata()
    
    if use_llm:
        try:
            metadata = await extract_metadata_with_llm(text, chat_model)
            if metadata.is_valid():
                return metadata
            logger.info("LLM 提取结果不完整，尝试启发式方法补充")
        except Exception as e:
            logger.warning(f"LLM 提取失败: {e}")
    
    # 使用启发式方法补充或作为备用
    heuristic_metadata = extract_metadata_from_text_heuristic(text)
    
    # 合并结果（LLM 结果优先）
    if not metadata.paper_title and heuristic_metadata.paper_title:
        metadata.paper_title = heuristic_metadata.paper_title
    if not metadata.doi and heuristic_metadata.doi:
        metadata.doi = heuristic_metadata.doi
    if not metadata.publication_year and heuristic_metadata.publication_year:
        metadata.publication_year = heuristic_metadata.publication_year
    if not metadata.abstract and heuristic_metadata.abstract:
        metadata.abstract = heuristic_metadata.abstract
    if not metadata.keywords and heuristic_metadata.keywords:
        metadata.keywords = heuristic_metadata.keywords
    if not metadata.references_count and heuristic_metadata.references_count:
        metadata.references_count = heuristic_metadata.references_count
    
    return metadata
