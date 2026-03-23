#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
片段高亮提取器 (PR-2 阶段D)

从完整的检索 chunk 中提取与用户问题最相关的 1-3 句话，
用于精确化引用溯源展示。

使用轻量级的关键词重叠方法，不调用 LLM，延迟 < 10ms。
"""

import re
from typing import Any, Dict, List, Tuple
from backend.config.log import get_logger
from backend.service.chunk_filter import (
    normalize_title_front_matter_text,
    is_title_page_metadata_text,
)

logger = get_logger(__name__)

_SUMMARY_QUESTION_HINTS = (
    '主要内容', '核心内容', '核心思想', '主要观点', '主要贡献', '摘要', '概述', '介绍',
    'main content', 'main idea', 'main contribution', 'summary', 'overview', 'what is this paper about'
)
_EXPERIMENT_QUESTION_HINTS = (
    '实验', '结果', '性能', '指标', '效果', '对比', '提升',
    'experiment', 'result', 'performance', 'metric', 'benchmark', 'accuracy'
)
_METHOD_QUESTION_HINTS = (
    '方法', '架构', '机制', '原理', '如何实现', '训练',
    'method', 'architecture', 'mechanism', 'training', 'approach'
)

_SUMMARY_SENTENCE_HINTS = (
    'abstract', 'we propose', 'we present', 'this paper', 'this work', 'in this paper',
    '本文', '提出', '介绍', '旨在', '目标', '核心', '贡献', '方法', '模型'
)
_METHOD_SENTENCE_HINTS = (
    'architecture', 'framework', 'model', 'module', 'token', 'projector', 'lora', 'diffusion',
    '训练', '架构', '机制', '模块', '交互标记', '投影器', '扩散', '对齐'
)
_MOTIVATION_SENTENCE_HINTS = (
    'lack', 'lacking', 'limitation', 'limitations', 'challenge', 'problem', 'issue',
    '忽视', '缺乏', '不足', '局限', '问题', '挑战'
)
_RESULT_SENTENCE_HINTS = (
    'result', 'results', 'benchmark', 'performance', 'accuracy', 'psnr', 'ssim', 'fid', 'iou',
    'outperform', 'outperforms', 'better than', 'superior',
    '实验', '结果', '性能', '准确率', '指标', '优于', '提升'
)
_RESULT_CONCLUSION_HINTS = (
    'outperform', 'outperforms', 'better than', 'superior', 'improve', 'improves',
    'results show', 'experiments show', 'we demonstrate', 'we show',
    '优于', '提升', '实验表明', '结果表明'
)
_EXPERIMENT_EVIDENCE_HINTS = (
    'experiment', 'experiments', 'evaluate', 'evaluation', 'benchmark', 'baseline', 'baselines',
    'compare', 'compares', 'comparison', 'localization', 'held-in', 'held in',
    '实验', '评估', '对比', '基线', '定位'
)
_TASK_LIST_HINTS = (
    'question answering', 'object detection', 'captioning', 'what-if',
    'b-box', 'bbox', 'detect', 'describe the task', 'task'
)

_CONTENT_START_HINTS = (
    'abstract', 'recent', 'in this paper', 'this paper', 'we propose', 'we present',
    'to this end', 'specifically', 'our primary focus', 'we build', 'experiments show',
    'results show', 'we demonstrate', '我们提出', '本文提出', '为此', '具体而言'
)

_HEADER_NOISE_RE = re.compile(
    r'(cvpr|iccv|eccv|neurips|iclr|aaai|arxiv|proceedings of|conference on|what should i do next)',
    re.IGNORECASE,
)

_DATE_NOISE_RE = re.compile(
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\b|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{4}\b',
    re.IGNORECASE,
)

_TABLE_METRIC_TOKEN_RE = re.compile(
    r'\b(psnr|lpips|ssim|fid|iou|acc|precision|recall|sim|top[- ]?1|top[- ]?5)\b',
    re.IGNORECASE,
)
_OCR_STICKY_FIXES = (
    (r'\bequipthe\b', 'equip the'),
    (r'\binthree\b', 'in three'),
    (r'\bweuse\b', 'we use'),
    (r'\bnewfamily\b', 'new family'),
    (r'\bthatare\b', 'that are'),
    (r'\bthatseamlessly\b', 'that seamlessly'),
    (r'\bthemodel\b', 'the model'),
    (r'\bandplanning\b', 'and planning'),
    (r'\borvideos\b', 'or videos'),
    (r'\btopof\b', 'top of'),
    (r'\bactiontokens\b', 'action tokens'),
)

# 中英文分句的正则表达式
_SENTENCE_SPLIT_RE = re.compile(
    r'(?<=[。！？；\.\!\?\;])\s*'   # 中英文句末标点后切分
    r'|(?<=\n)\s*'                  # 换行符切分
)

# 中英文分词用的简易模式（按非字母数字中文字符切分）
_TOKEN_RE = re.compile(r'[\w\u4e00-\u9fff]+', re.UNICODE)

# 停用词（高频但无信息量的词）
_STOP_WORDS = {
    # 中文停用词
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
    '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
    '没有', '看', '好', '自己', '这', '他', '她', '它', '这个', '那个',
    '可以', '以及', '通过', '使用', '进行', '其中', '对于', '并且',
    '但是', '如果', '或者', '因为', '所以', '而且', '虽然', '然而',
    '本文', '我们', '该', '其', '等', '及', '与', '被', '将', '从',
    # 英文停用词
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'as', 'into', 'through', 'during', 'before', 'after', 'above',
    'below', 'between', 'out', 'off', 'over', 'under', 'again',
    'further', 'then', 'once', 'and', 'but', 'or', 'nor', 'not',
    'so', 'than', 'too', 'very', 'just', 'about', 'that', 'this',
    'these', 'those', 'it', 'its', 'we', 'our', 'they', 'their',
}


def _normalize_snippet_content(content: str) -> str:
    """
    证据片段清洗：
    - 清理标题页前置元数据（容错粘连 abstract）
    - 对常见 OCR 粘连做轻量修复
    """
    if not content:
        return content
    
    cleaned = normalize_title_front_matter_text(content, min_content_length=30)
    
    # AbstractRecent -> Abstract Recent
    cleaned = re.sub(r'(?i)\babstract(?=[A-Z])', 'Abstract ', cleaned)
    # 3dvlaAbstract -> 3dvla Abstract
    cleaned = re.sub(r'([a-z0-9])(?=Abstract\b)', r'\1 ', cleaned)
    # AnsweringDetect -> Answering Detect, LocalizationTasks -> Localization Tasks
    cleaned = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', cleaned)
    # Experiments3D-VLA -> Experiments 3D-VLA
    cleaned = re.sub(r'(?<=[a-z])(?=\d[A-Z])', ' ', cleaned)
    for pattern, replacement in _OCR_STICKY_FIXES:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    # URL 与正文粘连：3dvlaAbstract... 已由上方处理，额外再压缩多空白
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    
    return cleaned


def _split_sentences(text: str) -> List[str]:
    """
    将文本切分为句子列表
    
    处理中英文混合文本，按句末标点和换行符切分。
    过短的片段（< 8字符）合并到前一个句子。
    """
    if not text or not text.strip():
        return []
    
    # 先按正则切分
    raw_sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    
    # 过滤空字符串
    raw_sentences = [s.strip() for s in raw_sentences if s and s.strip()]
    
    if not raw_sentences:
        return [text.strip()]
    
    # 合并过短的片段到前一个句子
    merged = []
    for sent in raw_sentences:
        if merged and len(sent) < 8:
            merged[-1] = merged[-1] + ' ' + sent
        else:
            merged.append(sent)
    
    return merged


def _tokenize(text: str) -> List[str]:
    """简易分词：提取所有中文字符和英文单词，转小写，去停用词"""
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _jaccard_similarity(set_a: set, set_b: set) -> float:
    """计算两个集合的 Jaccard 相似度"""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _detect_question_intent(question: str) -> str:
    lower = (question or '').lower()

    if any(hint in lower for hint in _EXPERIMENT_QUESTION_HINTS):
        return 'experiment'
    if any(hint in lower for hint in _METHOD_QUESTION_HINTS):
        return 'method'
    if any(hint in lower for hint in _SUMMARY_QUESTION_HINTS):
        return 'summary'
    return 'general'


def _sentence_label(sentence: str) -> str:
    compact = _trim_sentence_noise(sentence)
    lower = sentence.lower()
    if any(hint in lower for hint in _MOTIVATION_SENTENCE_HINTS):
        return '研究动机'
    if any(hint in lower for hint in _RESULT_SENTENCE_HINTS) or any(hint in lower for hint in _EXPERIMENT_EVIDENCE_HINTS):
        if _is_table_like_sentence(compact):
            return '指标结果'
        if any(hint in lower for hint in _RESULT_CONCLUSION_HINTS):
            return '实验结论'
        return '实验证据'
    if any(hint in lower for hint in _METHOD_SENTENCE_HINTS):
        if any(hint in lower for hint in ('train', 'training', 'build', 'utilize', 'token', 'diffusion', '训练', '构建', '利用', '标记', '扩散')):
            return '方法细节'
        return '方法证据'
    if any(hint in lower for hint in _SUMMARY_SENTENCE_HINTS):
        return '核心概述'
    return '相关证据'


def _sentence_role(sentence: str) -> str:
    lower = sentence.lower()
    if any(hint in lower for hint in _MOTIVATION_SENTENCE_HINTS):
        return 'motivation'
    if any(hint in lower for hint in _RESULT_SENTENCE_HINTS) or any(hint in lower for hint in _EXPERIMENT_EVIDENCE_HINTS):
        return 'experiment'
    if any(hint in lower for hint in _METHOD_SENTENCE_HINTS):
        return 'method'
    if any(hint in lower for hint in _SUMMARY_SENTENCE_HINTS):
        return 'summary'
    return 'general'


def _compact_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip()


def _looks_like_noise_prefix(text: str) -> bool:
    if not text:
        return False

    compact = _compact_whitespace(text)
    lower = compact.lower()
    signal_count = 0

    if 'what should i do next' in lower:
        signal_count += 2
    if _HEADER_NOISE_RE.search(compact):
        signal_count += 1
    if _DATE_NOISE_RE.search(compact):
        signal_count += 1
    if 'http://' in lower or 'https://' in lower or 'www.' in lower:
        signal_count += 1
    if compact.count(':') >= 2 and len(compact) < 220:
        signal_count += 1
    if len(re.findall(r'\d', compact)) >= 6 and len(compact) < 220:
        signal_count += 1

    return signal_count >= 2


def _trim_sentence_noise(sentence: str) -> str:
    compact = _compact_whitespace(sentence)
    if not compact:
        return ''

    cue_positions = []
    lower = compact.lower()
    for hint in _CONTENT_START_HINTS:
        position = lower.find(hint)
        if position > 0:
            cue_positions.append(position)

    if cue_positions:
        cut_index = min(cue_positions)
        prefix = compact[:cut_index]
        if _looks_like_noise_prefix(prefix):
            compact = compact[cut_index:].lstrip(' :;-.,)]}')

    compact = re.sub(r'^[\[\(]?\d+[\]\)]\s*', '', compact)
    compact = re.sub(r'^[,;]?\s*\d{4}\)\s*', '', compact)
    compact = re.sub(r"^[\"“”'`]+\s*", '', compact)
    compact = re.sub(r'^(?:abstract\s*[:：-]\s*)', 'Abstract ', compact, flags=re.IGNORECASE)
    compact = re.sub(r'^(?:keywords?\s*[:：-]\s*)', '', compact, flags=re.IGNORECASE)
    compact = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', compact)
    compact = re.sub(r'(?<=[a-z])(?=\d[A-Z])', ' ', compact)
    for pattern, replacement in _OCR_STICKY_FIXES:
        compact = re.sub(pattern, replacement, compact, flags=re.IGNORECASE)

    return compact.strip()


def _is_table_like_sentence(sentence: str) -> bool:
    compact = _compact_whitespace(sentence)
    number_count = len(re.findall(r'\b\d+(?:\.\d+)?\b', compact))
    metric_count = len(_TABLE_METRIC_TOKEN_RE.findall(compact))
    comma_count = compact.count(',')
    semicolon_count = compact.count(';')

    return (
        (metric_count >= 2 and number_count >= 4)
        or (number_count >= 6 and len(compact) < 240)
        or (metric_count >= 1 and (comma_count + semicolon_count) >= 4 and number_count >= 3)
    )


def _is_section_heading_like(sentence: str) -> bool:
    compact = _compact_whitespace(sentence)
    if not compact:
        return False

    lower = compact.lower()
    tokens = re.findall(r'[A-Za-z0-9\u4e00-\u9fff-]+', compact)
    if len(tokens) > 8:
        return False

    if re.search(r'\b(we|our|this paper|results show|experiments show|提出|模型|方法)\b', lower):
        return False

    heading_terms = ('section', 'task', 'tasks', 'reasoning', 'localization', 'framework', 'architecture')
    if not any(term in lower for term in heading_terms):
        return False

    has_sentence_verb = re.search(
        r'\b(is|are|show|shows|present|presents|introduce|introduces|propose|proposes|build|builds|utilize|utilizes|demonstrate|demonstrates|评估|提出|介绍)\b',
        lower,
    )
    return not bool(has_sentence_verb)


def _is_task_list_like(sentence: str) -> bool:
    compact = _compact_whitespace(sentence)
    if not compact:
        return False

    lower = compact.lower()
    hint_hits = sum(1 for hint in _TASK_LIST_HINTS if hint in lower)
    if hint_hits < 3:
        return False

    if any(signal in lower for signal in ('we ', 'our ', 'this paper', 'results', 'experiments', 'propose', 'build', 'utilize')):
        return False

    return True


def _is_fragment_like(sentence: str) -> bool:
    compact = _compact_whitespace(sentence)
    if not compact:
        return False

    lower = compact.lower()
    if lower.startswith(('to equip ', 'to inform ', 'to generate ', 'to provide ', 'to enable ')) and not lower.startswith('to this end'):
        return True
    if lower.startswith(('held-in evaluation', 'held in evaluation')):
        return True
    return False


def _is_experiment_setup_sentence(sentence: str) -> bool:
    lower = _compact_whitespace(sentence).lower()
    return lower.startswith((
        'held-in evaluation',
        'held in evaluation',
        'in this section, we evaluate',
        'we evaluate ',
        'we compare ',
        'our primary focus is on',
    ))


def _is_low_quality_sentence(sentence: str) -> bool:
    compact = _trim_sentence_noise(sentence)
    if not compact:
        return True

    lower = compact.lower()
    token_count = len(_tokenize(compact))

    if _is_section_heading_like(compact):
        return True
    if _is_task_list_like(compact):
        return True
    if 'what should i do next' in lower:
        return True
    if ('http://' in lower or 'https://' in lower or 'www.' in lower) and token_count < 14:
        return True
    if _looks_like_noise_prefix(compact) and token_count < 10:
        return True
    if _is_fragment_like(compact) and token_count < 10:
        return True
    if len(compact) < 24 and token_count < 4:
        return True

    return False


def _sentence_quality_adjustment(sentence: str, intent: str, position: int) -> float:
    compact = _trim_sentence_noise(sentence)
    lower = compact.lower()
    adjustment = 0.0

    if _is_section_heading_like(compact):
        adjustment -= 0.12
    if _is_task_list_like(compact):
        adjustment -= 0.14
    if _is_fragment_like(compact):
        adjustment -= 0.08
    if _is_table_like_sentence(compact):
        adjustment -= 0.075 if intent == 'experiment' else 0.12

    if _looks_like_noise_prefix(sentence):
        adjustment -= 0.08

    if re.match(r'^[a-z]-[a-z]+', lower):
        adjustment -= 0.03

    if compact[:1] in {'"', '“', '”', "'"}:
        adjustment -= 0.02

    if any(lower.startswith(hint) for hint in _CONTENT_START_HINTS):
        adjustment += 0.025

    role = _sentence_role(compact)
    if intent == 'method' and role == 'experiment':
        adjustment -= 0.05
    if intent == 'experiment' and role == 'method':
        adjustment -= 0.03
    if intent == 'summary' and role == 'experiment' and not any(token in lower for token in _RESULT_CONCLUSION_HINTS):
        adjustment -= 0.015

    if _is_experiment_setup_sentence(compact):
        adjustment -= 0.05 if intent == 'method' else 0.025

    if intent == 'experiment':
        if any(token in lower for token in _RESULT_CONCLUSION_HINTS):
            adjustment += 0.04
        if _is_table_like_sentence(compact) and any(token in lower for token in ('outperform', '优于', '提升')):
            adjustment += 0.02
        if _is_table_like_sentence(compact) and not any(token in lower for token in _RESULT_CONCLUSION_HINTS):
            adjustment -= 0.035

    if intent == 'summary' and position == 0 and any(token in lower for token in ('we propose', '本文提出', '我们提出', 'this paper')):
        adjustment += 0.03

    return adjustment


def _build_short_candidate_list(sentences: List[str], fallback_text: str, intent: str = 'general') -> List[Dict[str, Any]]:
    cleaned_sentences = [
        _trim_sentence_noise(sentence)
        for sentence in sentences
    ]
    cleaned_sentences = [
        sentence for sentence in cleaned_sentences
        if not _is_low_quality_sentence(sentence)
    ]

    if cleaned_sentences:
        candidates = []
        for idx, sentence in enumerate(cleaned_sentences):
            score = _intent_boost(sentence, intent, idx)
            score += _sentence_quality_adjustment(sentence, intent, idx)
            candidates.append({
                'text': sentence,
                'score': round(score, 4),
                'index': idx,
                'role': _sentence_role(sentence),
                'label': _sentence_label(sentence),
            })
        candidates.sort(key=lambda item: item['score'], reverse=True)
        return candidates

    fallback = _trim_sentence_noise(fallback_text)
    return [{
        'text': fallback,
        'score': 0.0,
        'index': 0,
        'role': _sentence_role(fallback),
        'label': _sentence_label(fallback),
    }]


def _intent_boost(sentence: str, intent: str, position: int) -> float:
    lower = sentence.lower()
    boost = 0.0

    if intent == 'summary':
        if any(hint in lower for hint in _SUMMARY_SENTENCE_HINTS):
            boost += 0.05
        if position <= 2:
            boost += 0.03
        if any(hint in lower for hint in _MOTIVATION_SENTENCE_HINTS):
            boost += 0.03
        if any(hint in lower for hint in _RESULT_SENTENCE_HINTS):
            boost -= 0.01
    elif intent == 'method':
        if any(hint in lower for hint in _METHOD_SENTENCE_HINTS):
            boost += 0.05
        if any(hint in lower for hint in _MOTIVATION_SENTENCE_HINTS):
            boost -= 0.01
    elif intent == 'experiment':
        if any(hint in lower for hint in _RESULT_SENTENCE_HINTS):
            boost += 0.05
        if re.search(r'\d+\.?\d*\s*%|\d+\.?\d*\s*倍|提升|提高|降低|减少|增加', sentence):
            boost += 0.02
        if _is_table_like_sentence(sentence) and not any(hint in lower for hint in _RESULT_CONCLUSION_HINTS):
            boost -= 0.02
    else:
        if any(hint in lower for hint in _SUMMARY_SENTENCE_HINTS):
            boost += 0.02
        if any(hint in lower for hint in _METHOD_SENTENCE_HINTS):
            boost += 0.02

    return boost


def extract_highlight_candidates(
    chunk_content: str,
    question: str,
    max_candidates: int = 3,
    min_score: float = 0.04
) -> List[Dict[str, Any]]:
    """提取多个候选证据句，便于前端展示更完整的证据覆盖。"""
    if not chunk_content or not chunk_content.strip():
        return []

    content = _normalize_snippet_content(chunk_content.strip())
    sentences = _split_sentences(content)
    intent = _detect_question_intent(question)

    if is_title_page_metadata_text(content):
        short_text = content[:180] + ('...' if len(content) > 180 else '')
        return [{
            'text': short_text,
            'score': 0.0,
            'index': 0,
            'role': 'summary',
            'label': '核心概述',
        }]

    if len(content) < 150:
        return _build_short_candidate_list(sentences, content, intent)[:max_candidates]

    if len(sentences) <= 2:
        return _build_short_candidate_list(sentences, content, intent)[:max_candidates]

    question_tokens = set(_tokenize(question))
    scored_sentences: List[Tuple[int, float, str]] = []
    for idx, sent in enumerate(sentences):
        cleaned_sent = _trim_sentence_noise(sent)
        if _is_low_quality_sentence(cleaned_sent):
            continue

        sent_tokens = set(_tokenize(cleaned_sent))
        score = _jaccard_similarity(question_tokens, sent_tokens) if question_tokens else 0.0
        score += _intent_boost(cleaned_sent, intent, idx)
        score += _sentence_quality_adjustment(cleaned_sent, intent, idx)
        scored_sentences.append((idx, score, cleaned_sent))

    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    selected: List[Tuple[int, float, str]] = []
    for idx, score, sent in scored_sentences:
        if score < min_score and selected:
            continue

        sent_tokens = set(_tokenize(sent))
        too_similar = False
        for _, _, existing in selected:
            existing_tokens = set(_tokenize(existing))
            if _jaccard_similarity(sent_tokens, existing_tokens) > 0.75:
                too_similar = True
                break

        if too_similar:
            continue

        selected.append((idx, score, sent))
        if len(selected) >= max_candidates:
            break

    if not selected and scored_sentences:
        selected = [scored_sentences[0]]

    if not selected:
        fallback = _trim_sentence_noise(content)
        return [{
            'text': fallback[:220] + ('...' if len(fallback) > 220 else ''),
            'score': 0.0,
            'index': 0,
            'role': _sentence_role(fallback),
            'label': _sentence_label(fallback),
        }]

    return [
        {
            'text': sent,
            'score': round(score, 4),
            'index': idx,
            'role': _sentence_role(sent),
            'label': _sentence_label(sent),
        }
        for idx, score, sent in selected
    ]


def extract_highlight(
    chunk_content: str,
    question: str,
    max_sentences: int = 3,
    min_score: float = 0.05
) -> str:
    """
    从完整 chunk 中提取与用户问题最相关的 1-3 句话
    
    Args:
        chunk_content: 完整的检索 chunk 文本
        question: 用户的原始问题
        max_sentences: 最多提取的句子数（默认3）
        min_score: 最低相关性阈值，低于此值的句子不会被提取
        
    Returns:
        提取的高亮文本（最相关的1-3句话）。
        如果整个 chunk 很短（< 150字），直接返回原文。
    """
    if not chunk_content or not chunk_content.strip():
        return chunk_content or ""
    
    content = _normalize_snippet_content(chunk_content.strip())
    
    # 兜底：如果仍像纯标题页元数据，则尽量返回更短的可读片段，避免整段“论文名片”
    if is_title_page_metadata_text(content):
        return content[:180] + ("..." if len(content) > 180 else "")
    
    # 如果内容本身就很短，也按句级候选做一次清洗和排序
    if len(content) < 150:
        short_candidates = _build_short_candidate_list(
            _split_sentences(content),
            content,
            _detect_question_intent(question),
        )
        return ' '.join(candidate['text'] for candidate in short_candidates[:max_sentences])
    
    # 分句
    sentences = _split_sentences(content)
    
    # 如果只有 1-2 个句子，直接返回
    if len(sentences) <= 2:
        short_candidates = _build_short_candidate_list(sentences, content, _detect_question_intent(question))
        return ' '.join(candidate['text'] for candidate in short_candidates[:max_sentences])
    
    # 对问题分词
    question_tokens = set(_tokenize(question))
    
    if not question_tokens:
        # 如果问题分词失败（极端情况），返回前几句
        return ' '.join(sentences[:max_sentences])
    
    candidates = extract_highlight_candidates(
        content,
        question,
        max_candidates=max_sentences,
        min_score=min_score,
    )

    highlight = ' '.join(candidate['text'] for candidate in candidates)

    if candidates:
        logger.debug(
            f"高亮提取: {len(sentences)} 句中选出 {len(candidates)} 句, "
            f"问题关键词: {question_tokens}, "
            f"最高分: {candidates[0]['score']:.3f}"
        )

    return highlight


def extract_context_window(
    chunk_content: str,
    anchor_text: str = "",
    window_chars: int = 260
) -> str:
    """
    从清洗后的 chunk 中截取一段更适合展示的上下文窗口。

    优先围绕高亮句附近取窗口；找不到锚点时返回开头片段。
    """
    if not chunk_content or not chunk_content.strip():
        return chunk_content or ""

    content = _normalize_snippet_content(chunk_content.strip())
    if len(content) <= window_chars:
        return content

    anchor = re.sub(r'\s+', ' ', (anchor_text or '').strip())
    content_lower = content.lower()
    anchor_lower = anchor.lower()

    anchor_index = -1
    if anchor and len(anchor) >= 12:
        anchor_index = content_lower.find(anchor_lower)

    if anchor_index < 0 and anchor:
        for token in _tokenize(anchor)[:4]:
            token_index = content_lower.find(token.lower())
            if token_index >= 0:
                anchor_index = token_index
                break

    if anchor_index < 0:
        excerpt = content[:window_chars].strip()
        return excerpt + ("..." if len(content) > window_chars else "")

    half_window = max(window_chars // 2, 80)
    start = max(anchor_index - half_window, 0)
    end = min(anchor_index + half_window, len(content))

    while start > 0 and content[start] not in '。！？.!?\n':
        start -= 1
    while end < len(content) and content[end - 1] not in '。！？.!?\n':
        end += 1

    excerpt = content[start:end].strip()
    if start > 0:
        excerpt = '...' + excerpt
    if end < len(content):
        excerpt = excerpt + '...'

    return excerpt
