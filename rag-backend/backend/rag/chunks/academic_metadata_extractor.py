#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学术元数据提取器 (PR-1)

从PDF文档中提取学术元数据：标题、作者、摘要、关键词、发表年份、DOI等
"""

import re
import json
from dataclasses import dataclass, asdict
from typing import Optional, List
import PyPDF2
from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class AcademicMetadata:
    """学术元数据结构"""
    academic_title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    publish_year: Optional[int] = None
    doi: Optional[str] = None
    source_type: str = "unknown"  # paper/web/book/document/unknown

    def to_dict(self) -> dict:
        """转换为字典，authors和keywords转为JSON字符串"""
        return {
            "academic_title": self.academic_title,
            "authors": json.dumps(self.authors, ensure_ascii=False) if self.authors else None,
            "abstract": self.abstract,
            "keywords": json.dumps(self.keywords, ensure_ascii=False) if self.keywords else None,
            "publish_year": self.publish_year,
            "doi": self.doi,
            "source_type": self.source_type
        }

    def is_empty(self) -> bool:
        """检查是否所有学术字段都为空"""
        return (
            self.academic_title is None and
            self.authors is None and
            self.abstract is None and
            self.keywords is None and
            self.publish_year is None and
            self.doi is None
        )


class AcademicMetadataExtractor:
    """学术元数据提取器"""

    def __init__(self):
        # DOI正则表达式
        self.doi_pattern = re.compile(r'10\.\d{4,}/[^\s]+')
        # 年份正则表达式（1900-2099）
        self.year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        # 摘要标识词
        self.abstract_markers = ['abstract', '摘要', 'summary']
        # 关键词标识词
        self.keyword_markers = ['keywords', 'key words', '关键词', 'index terms']

    def extract_from_pdf(self, file_path: str) -> AcademicMetadata:
        """
        从PDF文件提取学术元数据

        提取策略：
        1. 先从PDF内置元数据提取
        2. 再从正文首页补充缺失字段

        Args:
            file_path: PDF文件路径

        Returns:
            AcademicMetadata: 提取的元数据
        """
        metadata = AcademicMetadata(source_type="paper")

        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)

                # 步骤1：从PDF内置元数据提取
                self._extract_from_pdf_metadata(reader, metadata)

                # 步骤2：从正文首页补充
                if len(reader.pages) > 0:
                    first_page_text = reader.pages[0].extract_text() or ""
                    # 如果有第二页，也提取（摘要可能在第二页）
                    second_page_text = ""
                    if len(reader.pages) > 1:
                        second_page_text = reader.pages[1].extract_text() or ""

                    full_text = first_page_text + "\n" + second_page_text
                    self._extract_from_text(full_text, metadata)

                logger.info(f"PDF元数据提取完成: title={metadata.academic_title}, authors={metadata.authors}")

        except Exception as e:
            logger.error(f"PDF元数据提取失败: {str(e)}")
            # 提取失败不抛异常，返回空元数据

        return metadata

    def extract_from_text(self, text: str, source_type: str = "document") -> AcademicMetadata:
        """
        从纯文本提取学术元数据

        Args:
            text: 文本内容
            source_type: 来源类型

        Returns:
            AcademicMetadata: 提取的元数据
        """
        metadata = AcademicMetadata(source_type=source_type)
        self._extract_from_text(text, metadata)
        return metadata

    def _extract_from_pdf_metadata(self, reader: PyPDF2.PdfReader, metadata: AcademicMetadata):
        """从PDF内置元数据提取"""
        try:
            pdf_meta = reader.metadata
            if pdf_meta is None:
                return

            # 提取标题
            if pdf_meta.title and len(pdf_meta.title.strip()) > 0:
                title = pdf_meta.title.strip()
                # 过滤掉无意义的标题（如文件名、Microsoft Word等）
                if not self._is_invalid_title(title):
                    metadata.academic_title = title

            # 提取作者
            if pdf_meta.author and len(pdf_meta.author.strip()) > 0:
                author_str = pdf_meta.author.strip()
                # 尝试分割多个作者（常见分隔符：逗号、分号、and）
                authors = self._parse_authors(author_str)
                if authors:
                    metadata.authors = authors

            # 提取创建日期中的年份
            if hasattr(pdf_meta, 'creation_date') and pdf_meta.creation_date:
                try:
                    # PDF日期格式可能是 D:20231015... 或其他格式
                    date_str = str(pdf_meta.creation_date)
                    year_match = self.year_pattern.search(date_str)
                    if year_match:
                        metadata.publish_year = int(year_match.group())
                except:
                    pass

        except Exception as e:
            logger.warning(f"读取PDF内置元数据失败: {str(e)}")

    def _extract_from_text(self, text: str, metadata: AcademicMetadata):
        """从正文文本提取元数据"""
        if not text or len(text.strip()) == 0:
            return

        text_lower = text.lower()

        # 提取DOI（如果还没有）
        if metadata.doi is None:
            doi_match = self.doi_pattern.search(text)
            if doi_match:
                metadata.doi = doi_match.group().rstrip('.,;')

        # 提取年份（如果还没有）
        if metadata.publish_year is None:
            # 在DOI附近或文档开头找年份
            year_matches = self.year_pattern.findall(text[:2000])  # 只看前2000字符
            if year_matches:
                # 取最可能的年份（通常是较新的年份）
                years = [int(y) for y in year_matches]
                # 过滤掉不合理的年份
                valid_years = [y for y in years if 1990 <= y <= 2030]
                if valid_years:
                    metadata.publish_year = max(valid_years)

        # 提取摘要
        if metadata.abstract is None:
            metadata.abstract = self._extract_abstract(text, text_lower)

        # 提取关键词
        if metadata.keywords is None:
            metadata.keywords = self._extract_keywords(text, text_lower)

        # 如果标题还是空的，尝试从正文首行提取
        if metadata.academic_title is None:
            metadata.academic_title = self._extract_title_from_text(text)

    def _extract_abstract(self, text: str, text_lower: str) -> Optional[str]:
        """提取摘要"""
        for marker in self.abstract_markers:
            # 查找摘要标记的位置
            pos = text_lower.find(marker)
            if pos != -1:
                # 从标记后开始提取
                start = pos + len(marker)
                # 跳过可能的冒号、换行等
                while start < len(text) and text[start] in ':\n\r\t ':
                    start += 1

                # 找到下一个章节标记作为结束
                end_markers = ['introduction', '1.', '1 ', 'keywords', 'key words',
                               '关键词', '引言', '一、']
                end = len(text)
                remaining_text_lower = text_lower[start:]

                for end_marker in end_markers:
                    end_pos = remaining_text_lower.find(end_marker)
                    if end_pos != -1 and end_pos < end - start:
                        end = start + end_pos

                abstract = text[start:end].strip()

                # 清理和验证摘要
                abstract = self._clean_text(abstract)

                # 摘要应该有一定长度（至少50字符）
                if len(abstract) >= 50:
                    # 限制摘要长度（最多2000字符）
                    return abstract[:2000] if len(abstract) > 2000 else abstract

        return None

    def _extract_keywords(self, text: str, text_lower: str) -> Optional[List[str]]:
        """提取关键词"""
        for marker in self.keyword_markers:
            pos = text_lower.find(marker)
            if pos != -1:
                # 从标记后开始提取
                start = pos + len(marker)
                # 跳过可能的冒号、换行等
                while start < len(text) and text[start] in ':\n\r\t ':
                    start += 1

                # 提取到下一个换行或章节
                end = start
                while end < len(text) and end - start < 500:
                    if text[end] == '\n':
                        # 检查是否是双换行（段落结束）
                        if end + 1 < len(text) and text[end + 1] == '\n':
                            break
                    end += 1

                keywords_text = text[start:end].strip()

                # 分割关键词（常见分隔符：逗号、分号、·、;）
                keywords = re.split(r'[,;·；，、]', keywords_text)
                keywords = [k.strip() for k in keywords if k.strip()]

                # 过滤太长的词（可能不是关键词）
                keywords = [k for k in keywords if len(k) <= 50]

                if keywords:
                    return keywords[:10]  # 最多10个关键词

        return None

    def _extract_title_from_text(self, text: str) -> Optional[str]:
        """从正文开头提取标题"""
        lines = text.strip().split('\n')

        for line in lines[:5]:  # 只看前5行
            line = line.strip()
            # 标题通常是较短的行（10-200字符），不以小写字母开头
            if 10 <= len(line) <= 200:
                # 跳过明显不是标题的行
                if line.lower().startswith(('http', 'www', 'doi:', 'arxiv')):
                    continue
                if re.match(r'^\d+[\.\)]\s', line):  # 跳过编号行
                    continue
                # 可能是标题
                return self._clean_text(line)

        return None

    def _parse_authors(self, author_str: str) -> Optional[List[str]]:
        """解析作者字符串为作者列表"""
        if not author_str:
            return None

        # 常见分隔符
        separators = [';', ',', ' and ', '、', '，']

        authors = [author_str]
        for sep in separators:
            new_authors = []
            for a in authors:
                new_authors.extend(a.split(sep))
            authors = new_authors

        # 清理每个作者名
        authors = [a.strip() for a in authors if a.strip()]

        # 过滤掉太短或太长的名字
        authors = [a for a in authors if 2 <= len(a) <= 100]

        return authors if authors else None

    def _is_invalid_title(self, title: str) -> bool:
        """检查标题是否无效"""
        invalid_patterns = [
            r'^microsoft\s+word',
            r'^untitled',
            r'^document\d*$',
            r'\.pdf$',
            r'\.docx?$',
        ]
        title_lower = title.lower()

        for pattern in invalid_patterns:
            if re.search(pattern, title_lower):
                return True

        # 标题太短也无效
        if len(title) < 5:
            return True

        return False

    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 替换多个空白为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        text = text.strip()
        return text


# 全局单例
_extractor: Optional[AcademicMetadataExtractor] = None


def get_metadata_extractor() -> AcademicMetadataExtractor:
    """获取元数据提取器单例"""
    global _extractor
    if _extractor is None:
        _extractor = AcademicMetadataExtractor()
    return _extractor


def extract_academic_metadata(file_path: str, file_type: str = "pdf") -> AcademicMetadata:
    """
    提取学术元数据的便捷函数

    Args:
        file_path: 文件路径
        file_type: 文件类型 (pdf, docx, etc.)

    Returns:
        AcademicMetadata: 提取的元数据
    """
    extractor = get_metadata_extractor()

    if file_type.lower() == "pdf":
        return extractor.extract_from_pdf(file_path)
    else:
        # 其他类型暂时返回空元数据
        return AcademicMetadata(source_type="document")
