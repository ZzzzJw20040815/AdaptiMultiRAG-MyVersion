#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG检索结果过滤服务

提供多种过滤策略，过滤学术论文中的无用内容：
- 参考文献列表
- 作者贡献声明
- 致谢章节
- LaTeX源码残留
- 纯作者名单
- 联系方式/邮箱
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from backend.config.log import get_logger

logger = get_logger(__name__)


# ==================== P1: LaTeX 残留文本清理 ====================

# LaTeX 解析残留文本模式（需要移除的文本标签，不是 Unicode 符号）
LATEX_ARTIFACT_PATTERNS = [
    # 公式结构标签
    r'formulae-sequence',
    r'subscript',
    r'superscript',
    r'bold-italic',
    r'italic',
    r'bold',
    r'texttt',
    r'textbf',
    r'mathrm',
    r'mathbf',
    r'mathit',
    # 常见的乱码模式
    r'\{\\bf\s*',
    r'\\bf\s*',
    r'\\boldsymbol',
    r'\\texttt',
]

# 编译正则
_LATEX_CLEANUP_PATTERN = re.compile(
    '|'.join(LATEX_ARTIFACT_PATTERNS),
    re.IGNORECASE
)

# 连续空白字符清理
_WHITESPACE_PATTERN = re.compile(r'\s{3,}')


def clean_latex_artifacts(text: str) -> str:
    """
    清理 LaTeX 解析残留的文本标签
    
    注意：只清理文本标签（如 formulae-sequence），保留 Unicode 数学符号（如 𝐗、ϕ）
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    if not text:
        return text
    
    # 移除 LaTeX 残留标签
    cleaned = _LATEX_CLEANUP_PATTERN.sub('', text)
    
    # 合并连续空白字符（3个及以上空白合并为2个换行）
    cleaned = _WHITESPACE_PATTERN.sub('\n\n', cleaned)
    
    return cleaned.strip()


@dataclass
class ChunkFilterConfig:
    """
    检索结果过滤规则配置类
    
    Attributes:
        keyword_blacklist: 关键词黑名单，内容包含这些词则过滤（大小写不敏感）
        regex_patterns: 正则表达式模式列表，内容匹配到则过滤
        min_content_length: 最小内容长度，内容太短则过滤
        max_name_ratio: 最大人名比例，超过此比例认为是纯名单
        enabled: 是否启用过滤
    """
    keyword_blacklist: List[str] = field(default_factory=list)
    regex_patterns: List[str] = field(default_factory=list)
    min_content_length: int = 50
    max_name_ratio: float = 0.6
    enabled: bool = True


# 默认过滤规则配置 - 针对学术论文优化
DEFAULT_CHUNK_FILTER_CONFIG = ChunkFilterConfig(
    keyword_blacklist=[
        # ==================== 致谢章节标识 (P3 增强) ====================
        "we would like to acknowledge",
        "we thank",
        "we are grateful",
        "the authors thank",
        "acknowledgment",
        "acknowledgement",
        # P3 新增：致谢变体
        "we'd like to thank",
        "we would also like to thank",
        "we are also grateful",
        "finally, we thank",
        "the authors would like to thank",
        "we gratefully acknowledge",
        
        # ==================== 作者贡献标识 ====================
        "author contributions",
        "contributions:",
        "evaluations (ablations",
        "network architecture (tokenizer",
        "developed infrastructure",
        "leadership (managed",
        "paper (figures",
        "data collection and evaluations:",
        
        # ==================== 参考文献标识 ====================
        "references\n",
        "bibliography",
        "* ahn et al",
        "* brown et al",
        "* chen et al",
        "arXiv preprint arXiv:",
        "in proceedings of",
        "in conference on",
        "advances in neural information processing",
        "ieee international conference",
        "international conference on machine learning",
        
        # ==================== LaTeX残留 ====================
        "\\newfloatcommand",
        "\\correspondingauthor",
        "\\paperurl",
        "\\capbtabbox",
        "\\capbfigbox",
        "\\begin{",
        "\\end{",
        "\\FBwidth",
        
        # ==================== 通讯作者/邮箱 ====================
        "@google.com",
        "@deepmind.com",
        "@openai.com",
        "@meta.com",
        "@microsoft.com",
        "@stanford.edu",
        "@berkeley.edu",
        "@mit.edu",
        "@nvidia.com",
        "@facebook.com",
        "@amazon.com",
        
        # ==================== 版权声明 ====================
        "copyright ©",
        "all rights reserved",
        "creative commons",
        "open access article",
        
        # ==================== P3 改进：移除图注/表注的简单过滤 ====================
        # 注意：不再过滤 "figure 1:" 等，因为图注通常包含核心架构描述
        # 只过滤明显无意义的图表引用
        "see figure",  # 只是引用，非图注本身
        "shown in figure",
        "as shown in table",
        "refer to table",
        
        # ==================== P3 新增：软件包致谢 ====================
        "we'd also like to thank the developers",
        "software packages used",
        "numpy (harris et al",
        "scipy (virtanen et al",
        "pytorch (paszke et al",
        "tensorflow (abadi et al",
        
        # ==================== 纯碎片内容过滤 ====================
        # 注意：移除了 "et al." 过滤规则
        # 原因：该短语在学术论文正文中出现频率极高（如 "Smith et al. proposed..."）
        # 导致大量有效内容被误杀。参考文献格式由 regex_patterns 中的模式处理。
        
        # ==================== 附录内容过滤 (P4 新增) ====================
        # 过滤论文附录中的技术细节,如Prompt模板、超参数、格式说明等
        
        # Prompt 模板标识
        "prompt 1:",
        "prompt 2:",
        "prompt 3:",
        "prompt 4:",
        "prompt 5:",
        "prompt 6:",
        "prompt 7:",
        "prompt 8:",
        "prompt 9:",
        "prompt 10:",
        "prompt 11:",
        "prompt 12:",
        "llm output",
        "corrective summarization prompt",
        "summarization prompt",
        
        # 附录章节标识
        "appendix a",
        "appendix b",
        "appendix c",
        "appendix d",
        "supplementary material",
        "supplementary information",
        "more prompts",
        
        # 格式指令（LLM提示词中常见）
        "you must follow this format",
        "you always produce",
        "do not return any other string",
        "return the answer as a json",
        "let's think step by step",
        "explaining your reasoning before",
        
        # 超参数表格
        "hyperparameter value",
        "policy implementations",
        "model training hyperparameters",
    ],
    
    regex_patterns=[
        # 参考文献条目模式
        r"^\s*\*\s+[A-Z][a-z]+\s+et\s+al\.?\s*\(\d{4}\)",  # * Author et al. (2020)
        r"^\s*\[\d+\]\s+[A-Z][a-z]+",  # [1] Author name
        r"doi:\s*10\.\d{4,}",  # doi:10.xxxx
        r"arXiv:\d{4}\.\d+",  # arXiv:2404.xxxxx
        r"pmid:\s*\d+",  # PMID:123456
        r"isbn[:\s]*[\d\-]+",  # ISBN
        r"issn[:\s]*[\d\-]+",  # ISSN
        
        # LaTeX命令模式 - 只匹配明显的LaTeX命令，避免误杀
        r"\\newfloatcommand",  # 特定命令
        r"\\correspondingauthor",  # 特定命令
        
        # 作者贡献列表模式
        r"^\s*\*\s*•?\s*(Evaluations|Network Architecture|Developed Infrastructure|Leadership|Paper|Data collection):",
    ],
    
    min_content_length=50,
    max_name_ratio=0.6,
    enabled=True,
)


class ChunkFilterService:
    """
    RAG检索结果过滤服务
    
    过滤学术论文中的无用内容，提升检索质量。
    """
    
    def __init__(self, config: Optional[ChunkFilterConfig] = None):
        """
        初始化过滤服务
        
        Args:
            config: 过滤规则配置，如果为None则使用默认配置
        """
        self.config = config or DEFAULT_CHUNK_FILTER_CONFIG
        self._compiled_patterns: List[re.Pattern] = []
        self._compile_regex_patterns()
        
        logger.info(f"ChunkFilterService initialized: enabled={self.config.enabled}")
    
    def _compile_regex_patterns(self) -> None:
        """预编译正则表达式"""
        self._compiled_patterns = []
        for pattern in self.config.regex_patterns:
            try:
                self._compiled_patterns.append(
                    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
                )
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
    
    def filter_chunks(self, chunks: List) -> List:
        """
        过滤检索到的文档块
        
        Args:
            chunks: 检索到的文档列表（Document或RetrievedDocument对象）
            
        Returns:
            过滤后的文档列表
        """
        if not self.config.enabled:
            logger.debug("Chunk filtering is disabled")
            return chunks
        
        if not chunks:
            return chunks
        
        original_count = len(chunks)
        filtered_chunks = []
        filter_reasons = {}
        
        for i, chunk in enumerate(chunks):
            content = self._get_chunk_content(chunk)
            
            # P1: 先清理 LaTeX 残留文本
            cleaned_content = clean_latex_artifacts(content)
            
            # 如果有 page_content 属性，更新清理后的内容
            if hasattr(chunk, 'page_content') and cleaned_content != content:
                chunk.page_content = cleaned_content
            
            is_filtered, reason = self._should_filter_chunk(cleaned_content)
            
            if is_filtered:
                filter_reasons[f"chunk_{i}"] = reason
            else:
                filtered_chunks.append(chunk)
        
        filtered_count = original_count - len(filtered_chunks)
        logger.info(
            f"Chunk filtering complete: {len(filtered_chunks)} retained, "
            f"{filtered_count} filtered (from {original_count})"
        )
        
        # 记录过滤详情（使用INFO级别以便调试）
        if filter_reasons:
            logger.info(f"过滤详情: {filter_reasons}")
        
        return filtered_chunks
    
    def _get_chunk_content(self, chunk) -> str:
        """获取文档块的文本内容"""
        if hasattr(chunk, 'page_content'):
            return chunk.page_content or ""
        elif hasattr(chunk, 'content'):
            return chunk.content or ""
        elif isinstance(chunk, dict):
            return chunk.get('page_content', chunk.get('content', ''))
        return str(chunk)
    
    def _should_filter_chunk(self, content: str) -> Tuple[bool, Optional[str]]:
        """
        判断文档块是否应该被过滤
        
        Args:
            content: 文档块文本内容
            
        Returns:
            (是否过滤, 过滤原因)
        """
        if not content:
            return True, "empty_content"
        
        content = content.strip()
        
        # 1. 最小长度检查
        if len(content) < self.config.min_content_length:
            return True, f"too_short: {len(content)} < {self.config.min_content_length}"
        
        content_lower = content.lower()
        
        # 2. 关键词黑名单检查
        for keyword in self.config.keyword_blacklist:
            if keyword.lower() in content_lower:
                return True, f"keyword: '{keyword}'"
        
        # 3. 正则表达式检查
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(content):
                return True, f"regex: '{self.config.regex_patterns[i][:30]}...'"
        
        # 4. 纯名单检测（大量人名堆砌）
        if self._is_name_list(content):
            return True, "name_list_detected"
        
        return False, None
    
    def _is_name_list(self, content: str) -> bool:
        """
        检测是否为纯人名列表
        
        通过统计大写开头单词的比例来判断
        """
        words = content.split()
        if len(words) < 10:
            return False
        
        # 统计大写开头的单词（可能是人名）
        capitalized_words = sum(
            1 for word in words 
            if word and word[0].isupper() and word.isalpha()
        )
        
        ratio = capitalized_words / len(words)
        return ratio > self.config.max_name_ratio
    
    def update_config(self, **kwargs) -> None:
        """
        更新过滤配置
        
        Args:
            **kwargs: 要更新的配置项
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated chunk filter config: {key}={value}")
            else:
                logger.warning(f"Unknown config key: {key}")
        
        if "regex_patterns" in kwargs:
            self._compile_regex_patterns()
    
    def get_filter_stats(self, chunks: List) -> dict:
        """
        获取过滤统计信息（不实际过滤，仅统计）
        
        Args:
            chunks: 文档块列表
            
        Returns:
            统计信息字典
        """
        stats = {
            "total_chunks": len(chunks),
            "would_filter": {
                "by_length": 0,
                "by_keyword": 0,
                "by_regex": 0,
                "by_name_list": 0,
            },
            "would_retain": 0,
        }
        
        for chunk in chunks:
            content = self._get_chunk_content(chunk)
            is_filtered, reason = self._should_filter_chunk(content)
            
            if is_filtered:
                if reason and reason.startswith("too_short"):
                    stats["would_filter"]["by_length"] += 1
                elif reason and reason.startswith("keyword"):
                    stats["would_filter"]["by_keyword"] += 1
                elif reason and reason.startswith("regex"):
                    stats["would_filter"]["by_regex"] += 1
                elif reason == "name_list_detected":
                    stats["would_filter"]["by_name_list"] += 1
            else:
                stats["would_retain"] += 1
        
        return stats


# 全局单例（可选使用）
_chunk_filter_service: Optional[ChunkFilterService] = None


def get_chunk_filter_service() -> ChunkFilterService:
    """获取全局ChunkFilterService单例"""
    global _chunk_filter_service
    if _chunk_filter_service is None:
        _chunk_filter_service = ChunkFilterService()
    return _chunk_filter_service
