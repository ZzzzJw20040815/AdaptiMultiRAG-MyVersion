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

# 标题页/元数据识别
# 注意：这里不使用单纯的 \babstract\b，因 OCR 常见粘连形态如 "3dvlaAbstractRecent"
_ABSTRACT_TOKEN_RE = re.compile(r'abstract', re.IGNORECASE)
_URL_RE = re.compile(r'https?://|www\.', re.IGNORECASE)
_EMAIL_RE = re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b')
_AFFILIATION_RE = re.compile(
    r'\b(university|institute|department|school|college|laboratory|lab|research)\b',
    re.IGNORECASE
)
_NAME_TOKEN_RE = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b')
_SENTENCE_END_RE = re.compile(r'[.!?。！？]')
_NAME_WITH_DIGIT_RE = re.compile(r'[A-Z][a-z]{2,}\d+')
_DIGIT_PREFIXED_NAME_RE = re.compile(r'\d+[A-Z][a-z]{2,}')

# 图表交叉引用短句识别（只过滤“低信息量”的短片段）
_FIGURE_TABLE_REF_RE = re.compile(
    r'\b(?:as\s+shown\s+in|shown\s+in|see|refer\s+to)\s+(?:the\s+)?(?:figure|fig\.?|table)\b',
    re.IGNORECASE
)


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


def _find_abstract_start(content: str) -> Optional[int]:
    """
    宽松识别 abstract 起始位置，兼容 OCR 粘连文本（如 "3dvlaAbstractRecent"）。
    
    命中规则：
    - 命中 "abstract"（大小写不敏感）
    - 后续字符是分隔符、空白或大写字母（如 AbstractRecent）
    """
    if not content:
        return None
    
    for match in _ABSTRACT_TOKEN_RE.finditer(content):
        end_idx = match.end()
        next_char = content[end_idx:end_idx + 1]
        
        if not next_char:
            return match.start()
        if next_char.isspace() or next_char in ":：-—|/\\)]}":
            return match.start()
        if next_char.isupper():
            return match.start()
    
    return None


def looks_like_title_author_block(text: str) -> bool:
    """判断文本是否像论文标题页作者/单位元数据。"""
    if not text:
        return False
    
    words = re.findall(r'[\w\u4e00-\u9fff]+', text)
    if len(words) < 12:
        return False
    
    signal_count = 0
    
    if _URL_RE.search(text) or _EMAIL_RE.search(text):
        signal_count += 1
    
    if _AFFILIATION_RE.search(text):
        signal_count += 1
    
    if len(_NAME_TOKEN_RE.findall(text)) >= 6:
        signal_count += 1
    
    # OCR 常见姓名+编号粘连（如 Zhen1、Qiu1）
    if len(_NAME_WITH_DIGIT_RE.findall(text)) >= 3:
        signal_count += 1

    if len(_DIGIT_PREFIXED_NAME_RE.findall(text)) >= 2:
        signal_count += 1
    
    if len(re.findall(r'\d', text)) >= 5:
        signal_count += 1
    
    # URL 中 "." 会干扰句子统计，先移除 URL 再计数
    text_without_url = _URL_RE.sub(' ', text)
    if len(_SENTENCE_END_RE.findall(text_without_url)) <= 1:
        signal_count += 1
    
    return signal_count >= 3


def normalize_title_front_matter_text(content: str, min_content_length: int = 50) -> str:
    """
    清理标题页元数据前缀，仅保留 abstract 及其后的正文。
    """
    if not content:
        return content
    
    abstract_idx = _find_abstract_start(content)
    if abstract_idx is None:
        return content
    
    if abstract_idx <= 40:
        return content
    
    # abstract 应位于 chunk 前半段，避免误切正文
    if abstract_idx > min(1200, int(len(content) * 0.7)):
        return content
    
    prefix = content[:abstract_idx].strip()
    if not looks_like_title_author_block(prefix):
        return content
    
    normalized = content[abstract_idx:].strip()
    if len(normalized) < min_content_length:
        return content
    
    # 粘连修复: AbstractRecent -> Abstract Recent
    normalized = re.sub(r'(?i)\babstract(?=[A-Z])', 'Abstract ', normalized)
    
    return normalized


def is_title_page_metadata_text(content: str) -> bool:
    """
    识别纯标题页元数据（无有效正文）文本。
    """
    if not content:
        return False
    
    if len(content) > 1400:
        return False
    
    if not looks_like_title_author_block(content):
        return False
    
    # 若已包含 abstract，优先走前缀清理，不直接判纯元数据
    if _find_abstract_start(content) is not None:
        return False
    
    body_signal = re.search(
        r'\b(introduction|method|methods|experiment|results?|conclusion|'
        r'模型|方法|实验|结果|结论)\b',
        content,
        re.IGNORECASE
    )
    if body_signal:
        return False
    
    return True


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
        "author contributions:",
        "evaluations (ablations",
        "network architecture (tokenizer",
        "developed infrastructure",
        "leadership (managed",
        "paper (figures",
        "data collection and evaluations:",
        
        # ==================== 参考文献标识（仅保留明确的参考文献章节标题） ====================
        # 注意: 单独出现的 "arXiv preprint arXiv:" 等在正文中很常见（如 "Smith et al. arXiv preprint arXiv:2404..."）
        # 这些已移到 _is_reference_section() 方法中做密度检测，避免误杀正文
        "references\n",
        "bibliography",
        
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
        
        # ==================== P3 改进：图/表引用不再做硬关键词过滤 ====================
        # 原始规则会误杀正文（如“如图所示，模型架构包含...”）。
        # 现在改为在 _is_low_info_figure_table_reference 中仅过滤“低信息量短片段”。
        
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
        # 参考文献条目模式（仅匹配明确的条目格式）
        r"^\s*\*\s+[A-Z][a-z]+\s+et\s+al\.?\s*\(\d{4}\)",  # * Author et al. (2020)
        r"^\s*\[\d+\]\s+[A-Z][a-z]+",  # [1] Author name
        r"doi:\s*10\.\d{4,}",  # doi:10.xxxx
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
            # P2: 清理标题页前置元数据（标题/作者/单位/URL 等），保留 abstract 后正文
            normalized_content = self._normalize_title_front_matter(cleaned_content)
            
            # 如果有 page_content 属性，更新清理后的内容
            if hasattr(chunk, 'page_content') and normalized_content != content:
                chunk.page_content = normalized_content
            if hasattr(chunk, 'metadata') and isinstance(chunk.metadata, dict):
                chunk.metadata["title_front_matter_cleaned"] = normalized_content != content
                if normalized_content != content:
                    chunk.metadata["title_front_matter_removed_chars"] = max(len(content) - len(normalized_content), 0)
            
            is_filtered, reason = self._should_filter_chunk(normalized_content)
            
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
        
        # 3. 图表交叉引用短片段检测（放宽规则，仅过滤低信息量短句）
        if self._is_low_info_figure_table_reference(content):
            return True, "low_info_figure_table_reference"
        
        # 4. 正则表达式检查
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(content):
                return True, f"regex: '{self.config.regex_patterns[i][:30]}...'"
        
        # 5. 标题页元数据检测（论文标题 + 作者名单 + 单位/URL）
        if self._is_title_page_metadata_chunk(content):
            return True, "title_page_metadata_detected"
        
        # 6. 纯名单检测（大量人名堆砌）
        if self._is_name_list(content):
            return True, "name_list_detected"
        
        # 7. 参考文献章节密度检测（PR-2 改进）
        if self._is_reference_section(content):
            return True, "reference_section_detected"
        
        return False, None
    
    def _normalize_title_front_matter(self, content: str) -> str:
        """
        清理标题页元数据前缀，避免“论文名片 + 摘要开头”混入同一证据片段。
        
        策略：
        - 当检测到内容中存在 abstract，并且 abstract 前缀明显是标题页元数据块时，
          仅保留 abstract 及其后的正文。
        """
        return normalize_title_front_matter_text(
            content,
            min_content_length=self.config.min_content_length
        )
    
    def _looks_like_title_author_block(self, text: str) -> bool:
        """判断一段文本是否像论文标题页的作者/单位元数据块。"""
        return looks_like_title_author_block(text)
    
    def _is_title_page_metadata_chunk(self, content: str) -> bool:
        """
        识别纯标题页元数据 chunk（无有效正文）。
        
        主要命中：
        - 标题 + 作者名单 + 单位/URL + 极少句号
        - 没有 method/result/experiment 等正文信号
        """
        return is_title_page_metadata_text(content)
    
    def _is_low_info_figure_table_reference(self, content: str) -> bool:
        """
        仅过滤“低信息量”的图/表交叉引用短片段。
        
        说明：
        - 不再把 “shown in figure / as shown in table” 当作硬黑名单。
        - 只有当内容较短、且不包含方法/结果类信息时才过滤。
        """
        if not content:
            return False
        
        if len(content) > 220:
            return False
        
        if not _FIGURE_TABLE_REF_RE.search(content):
            return False
        
        lower = content.lower()
        informative_keywords = [
            "propose", "model", "method", "architecture", "experiment", "result",
            "dataset", "performance", "framework", "approach",
            "模型", "方法", "实验", "结果", "数据集", "性能"
        ]
        if any(keyword in lower for keyword in informative_keywords):
            return False
        
        return True
    
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
    
    def _is_reference_section(self, content: str) -> bool:
        """
        密度检测: 判断 chunk 是否为参考文献章节
        
        不再用单个关键词匹配，而是统计多个参考文献指示符的密度。
        只有当 chunk 中出现 3+ 个参考文献指示符时才认为是参考文献章节。
        这样正文中偶尔提到的 arXiv 引用不会被误杀。
        """
        content_lower = content.lower()
        
        # 参考文献指示符列表
        ref_indicators = [
            "arXiv preprint arXiv:",
            "arXiv preprint,",
            "in proceedings of",
            "in conference on",
            "advances in neural information processing",
            "ieee international conference",
            "international conference on machine learning",
            "* ahn et al",
            "* brown et al",
            "* chen et al",
            "* wang et al",
            "* liu et al",
            "* zhang et al",
            "et al., 20",  # 常见参考文献格式: Author et al., 2023
        ]
        
        # 统计命中数
        hit_count = sum(1 for ind in ref_indicators if ind.lower() in content_lower)
        
        # 补充: 统计 arXiv:数字 模式的出现次数
        arxiv_matches = len(re.findall(r'arXiv:\d{4}\.\d+', content, re.IGNORECASE))
        hit_count += arxiv_matches
        
        # 只有当命中 3 个及以上指示符时，才认为是参考文献章节
        return hit_count >= 3
    
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
