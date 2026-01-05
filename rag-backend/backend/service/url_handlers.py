#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL 处理器模块 (PR-4)
提供 URL 类型检测和专用处理逻辑
"""
import re
import asyncio
import aiohttp
import tempfile
import os
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from urllib.parse import urlparse, parse_qs

from backend.config.log import get_logger

logger = get_logger(__name__)


class URLType(str, Enum):
    """URL 类型枚举"""
    ARXIV = "arxiv"              # arXiv 论文
    PDF = "pdf"                  # 直接 PDF 链接
    WEBPAGE = "webpage"          # 普通网页
    UNKNOWN = "unknown"          # 未知类型


class URLInfo:
    """URL 解析信息"""
    def __init__(
        self,
        original_url: str,
        url_type: URLType,
        normalized_url: str,
        arxiv_id: Optional[str] = None,
        pdf_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.original_url = original_url
        self.url_type = url_type
        self.normalized_url = normalized_url
        self.arxiv_id = arxiv_id  # arXiv 论文 ID (如 2301.12345)
        self.pdf_url = pdf_url    # PDF 下载链接
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_url": self.original_url,
            "url_type": self.url_type.value,
            "normalized_url": self.normalized_url,
            "arxiv_id": self.arxiv_id,
            "pdf_url": self.pdf_url,
            "metadata": self.metadata,
        }


def detect_url_type(url: str) -> URLInfo:
    """
    检测 URL 类型并解析相关信息
    
    Args:
        url: 输入 URL
        
    Returns:
        URLInfo: URL 解析信息
    """
    url = url.strip()
    parsed = urlparse(url)
    
    # 1. 检测 arXiv URL
    arxiv_patterns = [
        # https://arxiv.org/abs/2301.12345
        r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)',
        # https://arxiv.org/pdf/2301.12345.pdf
        r'arxiv\.org/pdf/(\d{4}\.\d{4,5}(?:v\d+)?)(?:\.pdf)?',
        # https://ar5iv.labs.arxiv.org/html/2301.12345
        r'ar5iv\.labs\.arxiv\.org/html/(\d{4}\.\d{4,5}(?:v\d+)?)',
        # 旧格式: arxiv.org/abs/cs/0123456
        r'arxiv\.org/abs/([a-z\-]+/\d{7}(?:v\d+)?)',
    ]
    
    for pattern in arxiv_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            arxiv_id = match.group(1)
            # 规范化 arXiv URL
            normalized_url = f"https://arxiv.org/abs/{arxiv_id}"
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            logger.info(f"检测到 arXiv URL: {arxiv_id}")
            return URLInfo(
                original_url=url,
                url_type=URLType.ARXIV,
                normalized_url=normalized_url,
                arxiv_id=arxiv_id,
                pdf_url=pdf_url,
                metadata={"source": "arxiv"}
            )
    
    # 2. 检测直接 PDF 链接
    if url.lower().endswith('.pdf'):
        logger.info(f"检测到 PDF URL: {url}")
        return URLInfo(
            original_url=url,
            url_type=URLType.PDF,
            normalized_url=url,
            pdf_url=url,
            metadata={"source": "direct_pdf"}
        )
    
    # 3. 检测 URL 中的 PDF 参数
    query_params = parse_qs(parsed.query)
    if 'pdf' in parsed.path.lower() or any('pdf' in str(v).lower() for v in query_params.values()):
        logger.info(f"检测到可能的 PDF URL: {url}")
        return URLInfo(
            original_url=url,
            url_type=URLType.PDF,
            normalized_url=url,
            pdf_url=url,
            metadata={"source": "pdf_param"}
        )
    
    # 4. 默认为普通网页
    logger.info(f"检测为普通网页 URL: {url}")
    return URLInfo(
        original_url=url,
        url_type=URLType.WEBPAGE,
        normalized_url=url,
        metadata={"source": "webpage"}
    )


async def download_pdf(url: str, timeout: int = 60) -> Tuple[Optional[bytes], Optional[str]]:
    """
    下载 PDF 文件
    
    Args:
        url: PDF URL
        timeout: 超时时间（秒）
        
    Returns:
        Tuple[bytes, str]: (PDF 内容, 错误信息)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            ) as response:
                if response.status == 200:
                    content = await response.read()
                    content_type = response.headers.get('Content-Type', '')
                    
                    # 验证是否为 PDF
                    if 'application/pdf' in content_type or content[:4] == b'%PDF':
                        logger.info(f"成功下载 PDF: {len(content)} bytes")
                        return content, None
                    else:
                        return None, f"内容类型不是 PDF: {content_type}"
                else:
                    return None, f"HTTP 错误: {response.status}"
                    
    except asyncio.TimeoutError:
        return None, "下载超时"
    except Exception as e:
        return None, f"下载失败: {str(e)}"


async def fetch_arxiv_metadata(arxiv_id: str) -> Dict[str, Any]:
    """
    从 arXiv API 获取论文元数据
    
    Args:
        arxiv_id: arXiv 论文 ID
        
    Returns:
        Dict: 论文元数据
    """
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # 解析 Atom XML 响应
                    metadata = _parse_arxiv_atom(content)
                    if metadata:
                        logger.info(f"成功获取 arXiv 元数据: {arxiv_id}")
                        return metadata
                    else:
                        logger.warning(f"解析 arXiv 元数据失败: {arxiv_id}")
                        return {}
                else:
                    logger.warning(f"arXiv API 返回错误: {response.status}")
                    return {}
                    
    except Exception as e:
        logger.error(f"获取 arXiv 元数据失败: {e}")
        return {}


def _parse_arxiv_atom(xml_content: str) -> Dict[str, Any]:
    """
    解析 arXiv Atom XML 响应
    
    Args:
        xml_content: XML 内容
        
    Returns:
        Dict: 解析的元数据
    """
    import xml.etree.ElementTree as ET
    
    try:
        # 定义命名空间
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        root = ET.fromstring(xml_content)
        entry = root.find('atom:entry', namespaces)
        
        if entry is None:
            return {}
        
        # 提取元数据
        title_elem = entry.find('atom:title', namespaces)
        summary_elem = entry.find('atom:summary', namespaces)
        published_elem = entry.find('atom:published', namespaces)
        
        # 提取作者
        authors = []
        for author in entry.findall('atom:author', namespaces):
            name = author.find('atom:name', namespaces)
            if name is not None:
                authors.append(name.text)
        
        # 提取分类
        categories = []
        for category in entry.findall('atom:category', namespaces):
            term = category.get('term')
            if term:
                categories.append(term)
        
        # 提取 DOI (如果有)
        doi = None
        for link in entry.findall('atom:link', namespaces):
            if link.get('title') == 'doi':
                doi = link.get('href')
                if doi and doi.startswith('http://dx.doi.org/'):
                    doi = doi.replace('http://dx.doi.org/', '')
        
        metadata = {
            'paper_title': title_elem.text.strip().replace('\n', ' ') if title_elem is not None else None,
            'abstract': summary_elem.text.strip().replace('\n', ' ') if summary_elem is not None else None,
            'authors': authors,
            'publication_year': int(published_elem.text[:4]) if published_elem is not None else None,
            'keywords': categories[:5],  # 取前 5 个分类作为关键词
            'doi': doi,
            'publication_venue': 'arXiv',
        }
        
        return metadata
        
    except Exception as e:
        logger.error(f"解析 arXiv XML 失败: {e}")
        return {}


async def process_arxiv_url(url_info: URLInfo) -> Dict[str, Any]:
    """
    处理 arXiv URL
    
    Args:
        url_info: URL 信息
        
    Returns:
        Dict: 处理结果，包含元数据和 PDF 内容路径
    """
    result = {
        "success": False,
        "url_type": URLType.ARXIV.value,
        "arxiv_id": url_info.arxiv_id,
        "metadata": {},
        "pdf_path": None,
        "error": None,
    }
    
    try:
        # 1. 获取 arXiv 元数据
        if url_info.arxiv_id:
            metadata = await fetch_arxiv_metadata(url_info.arxiv_id)
            result["metadata"] = metadata
        
        # 2. 下载 PDF
        if url_info.pdf_url:
            pdf_content, error = await download_pdf(url_info.pdf_url)
            
            if pdf_content:
                # 保存到临时文件
                with tempfile.NamedTemporaryFile(
                    suffix='.pdf', 
                    delete=False, 
                    prefix=f"arxiv_{url_info.arxiv_id}_"
                ) as f:
                    f.write(pdf_content)
                    result["pdf_path"] = f.name
                    result["success"] = True
                    logger.info(f"arXiv PDF 保存到: {f.name}")
            else:
                result["error"] = f"PDF 下载失败: {error}"
                logger.warning(result["error"])
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"处理 arXiv URL 失败: {e}")
        return result


async def process_pdf_url(url_info: URLInfo) -> Dict[str, Any]:
    """
    处理直接 PDF URL
    
    Args:
        url_info: URL 信息
        
    Returns:
        Dict: 处理结果
    """
    result = {
        "success": False,
        "url_type": URLType.PDF.value,
        "pdf_path": None,
        "error": None,
    }
    
    try:
        pdf_content, error = await download_pdf(url_info.pdf_url)
        
        if pdf_content:
            # 从 URL 提取文件名
            parsed = urlparse(url_info.original_url)
            filename = os.path.basename(parsed.path) or "document.pdf"
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(
                suffix='.pdf', 
                delete=False, 
                prefix="pdf_"
            ) as f:
                f.write(pdf_content)
                result["pdf_path"] = f.name
                result["success"] = True
                logger.info(f"PDF 保存到: {f.name}")
        else:
            result["error"] = f"PDF 下载失败: {error}"
            logger.warning(result["error"])
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"处理 PDF URL 失败: {e}")
        return result


async def smart_url_process(url: str) -> Dict[str, Any]:
    """
    智能 URL 处理入口
    
    根据 URL 类型自动选择处理方式：
    - arXiv: 获取元数据 + 下载 PDF
    - PDF: 直接下载
    - 网页: 返回标记，交由爬虫处理
    
    Args:
        url: 输入 URL
        
    Returns:
        Dict: 处理结果
    """
    # 1. 检测 URL 类型
    url_info = detect_url_type(url)
    
    # 2. 根据类型处理
    if url_info.url_type == URLType.ARXIV:
        return await process_arxiv_url(url_info)
    
    elif url_info.url_type == URLType.PDF:
        return await process_pdf_url(url_info)
    
    else:
        # 网页类型，返回标记让调用方使用爬虫处理
        return {
            "success": True,
            "url_type": URLType.WEBPAGE.value,
            "should_crawl": True,
            "normalized_url": url_info.normalized_url,
            "error": None,
        }
