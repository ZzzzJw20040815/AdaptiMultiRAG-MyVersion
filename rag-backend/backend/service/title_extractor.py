#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论文标题提取服务

从上传的 PDF 文档中自动提取论文标题，用于支持白名单机制。
"""

import re
from typing import Optional
from backend.config.log import get_logger

logger = get_logger(__name__)


def extract_title_from_text(text: str, max_lines: int = 20) -> Optional[str]:
    """
    从文档文本内容中提取论文标题
    
    策略：
    1. 取文档前 N 行
    2. 跳过空行、页眉页脚等无关内容
    3. 寻找最可能是标题的行（通常是第一个有意义的非短文本行）
    
    Args:
        text: 文档文本内容
        max_lines: 分析的最大行数
        
    Returns:
        提取的标题，如果无法提取则返回 None
    """
    if not text or not text.strip():
        logger.warning("文本内容为空，无法提取标题")
        return None
    
    # 按行分割
    lines = text.strip().split('\n')
    
    # 用于过滤的模式
    skip_patterns = [
        # arXiv 标识
        r'^arXiv:\s*\d+\.\d+',
        # 日期模式
        r'^\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}',
        # 页码
        r'^(page\s*)?\d+(\s+of\s+\d+)?$',
        r'^\d+$',
        # 版权信息
        r'^©|^copyright|^all rights reserved',
        # URL
        r'^(https?://|www\.)',
        # 邮箱
        r'^[\w\.-]+@[\w\.-]+',
        # 常见页眉
        r'^(abstract|introduction|keywords|contents)$',
        # 期刊信息
        r'^(journal|proceedings|conference|accepted|submitted|published)',
        # 纯数字或特殊字符
        r'^[\d\s\-\.\,\:\;]+$',
        # 预印本/草稿标记
        r'^(preprint|draft|working paper|technical report)',
    ]
    
    # 编译正则表达式
    skip_regex = [re.compile(p, re.IGNORECASE) for p in skip_patterns]
    
    candidate_titles = []
    
    for i, line in enumerate(lines[:max_lines]):
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
        
        # 跳过太短的行（少于 5 个字符，可能是编号等）
        if len(line) < 5:
            continue
        
        # 跳过太长的行（超过 300 个字符，可能是段落）
        if len(line) > 300:
            continue
        
        # 检查是否匹配跳过模式
        should_skip = False
        for regex in skip_regex:
            if regex.search(line):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        # 跳过以小写字母开头的行（可能是段落的一部分）
        # 但保留中文开头的行
        if line[0].islower() and not re.match(r'^[\u4e00-\u9fff]', line):
            continue
        
        # 计算标题可能性得分
        score = 0
        
        # 标题通常不以句号结尾
        if not line.endswith('.') and not line.endswith('。'):
            score += 2
        
        # 标题通常不包含 "we"、"this paper"、"in this" 等
        if not re.search(r'\b(we|this paper|in this|our|these)\b', line, re.IGNORECASE):
            score += 1
        
        # 标题通常较短（20-150 字符）
        if 20 <= len(line) <= 150:
            score += 2
        elif 10 <= len(line) < 20:
            score += 1
        
        # 如果包含冒号，可能是标题（例如 "BERT: Pre-training of..."）
        if ':' in line or '：' in line:
            score += 1
        
        # 前几行得分更高
        if i < 5:
            score += 2
        elif i < 10:
            score += 1
        
        # 全大写词汇较多可能是标题
        words = line.split()
        if words:
            upper_ratio = sum(1 for w in words if w.isupper() and len(w) > 1) / len(words)
            if upper_ratio > 0.3:
                score += 1
        
        candidate_titles.append((score, line, i))  # 加入行索引 i
    
    if not candidate_titles:
        logger.warning("未找到合适的标题候选")
        return None
    
    # 按得分排序，取最高分
    candidate_titles.sort(key=lambda x: x[0], reverse=True)
    best_score, best_title, best_idx = candidate_titles[0]
    
    # ==================== 多行标题合并逻辑 ====================
    # 如果标题以冒号结尾（如 "ChatGPT for Robotics:"），尝试合并下一行
    if best_title.endswith(':') or best_title.endswith('：'):
        next_idx = best_idx + 1
        # 查找下一行有效内容（跳过空行）
        while next_idx < min(len(lines), max_lines):
            next_line = lines[next_idx].strip()
            if next_line:
                break
            next_idx += 1
        
        if next_idx < len(lines):
            next_line = lines[next_idx].strip()
            # 检查下一行是否适合作为副标题
            # 条件：不以句号结尾、长度合适、不是段落开头
            is_valid_subtitle = (
                next_line and
                len(next_line) >= 5 and
                len(next_line) <= 200 and
                not next_line.endswith('.') and
                not next_line.endswith('。') and
                not next_line[0].islower()  # 不以小写字母开头
            )
            
            if is_valid_subtitle:
                # 合并为完整标题
                combined_title = f"{best_title} {next_line}"
                logger.info(f"检测到多行标题，合并: '{best_title}' + '{next_line}'")
                best_title = combined_title
    
    # 清理标题
    # 移除多余空格
    best_title = ' '.join(best_title.split())
    
    # 截断过长标题
    if len(best_title) > 200:
        best_title = best_title[:200] + "..."
    
    logger.info(f"提取到标题: {best_title}")
    return best_title


def extract_title_from_pdf_first_page(file_path: str) -> Optional[str]:
    """
    从 PDF 文件第一页提取标题
    
    Args:
        file_path: PDF 文件路径
        
    Returns:
        提取的标题，如果无法提取则返回 None
    """
    try:
        import PyPDF2
        
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            if len(reader.pages) == 0:
                logger.warning("PDF 文件没有页面")
                return None
            
            # 只读取第一页
            first_page = reader.pages[0]
            text = first_page.extract_text()
            
            if not text:
                logger.warning("第一页没有提取到文本")
                return None
            
            return extract_title_from_text(text)
            
    except Exception as e:
        logger.error(f"PDF 标题提取失败: {str(e)}")
        return None
