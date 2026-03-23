#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点类型分类器

基于规则的节点语义类型分类，将实体名称/描述映射到有意义的类型分类。
不依赖 LLM，完全基于关键词和模式匹配。
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from backend.config.log import get_logger

logger = get_logger(__name__)


@dataclass
class SemanticTypeConfig:
    """语义类型配置"""
    # 类型名称（中文）
    name: str
    # 关键词列表（匹配实体名称或描述）
    keywords: List[str] = field(default_factory=list)
    # 正则表达式模式（匹配实体名称）
    patterns: List[str] = field(default_factory=list)
    # 描述模式（匹配描述内容，用于语义分析）
    description_patterns: List[str] = field(default_factory=list)
    # 优先级（数字越小优先级越高）
    priority: int = 100


# 预定义的语义类型配置
# 注意：优先级数字越小越优先匹配，需要仔细调整避免误分类
SEMANTIC_TYPE_CONFIGS: List[SemanticTypeConfig] = [
    # 数据集类型 - 优先级最高，避免被其他类型误匹配（如 ImageNet 不应被 "net" 模式匹配到模型）
    SemanticTypeConfig(
        name="数据集",
        keywords=[
            "dataset", "benchmark", "corpus", "collection", "data",
            "imagenet", "coco", "mnist", "cifar", "squad", "glue", "wmt",
            "openwebtext", "pile", "laion", "cc3m", "vqa", "mscoco",
            "training data", "test set", "validation set", "eval set",
            "annotation", "labeled", "labelled", "samples",
        ],
        patterns=[
            r"(?i)^.*(dataset|benchmark|corpus).*$",
            r"(?i)^(imagenet|coco|mnist|cifar|squad|glue|wmt|vqa)",  # 常见数据集名称开头
        ],
        priority=5  # 最高优先级
    ),
    
    # 人物类型 - 使用描述模式和精确人名模式
    SemanticTypeConfig(
        name="人物",
        keywords=[
            # 只保留不容易误匹配的关键词
            "researcher at", "professor at", "scientist at", "student at",
            "engineer at", "developer at", "founder of", "ceo of", "cto of",
            "authored by", "proposed by", "introduced by",
        ],
        patterns=[
            # 标准人名格式
            r"^[A-Z][a-z]+\s+[A-Z][a-z]+$",  # 两个单词的人名（如 "John Smith"）
            r"^[A-Z]\.\s*[A-Z][a-z]+$",  # 缩写名（如 "J. Smith"）
            r"^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+$",  # 中间名缩写（如 "John A. Smith"）
            r"^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+$",  # 三个单词的人名
            r"^Dr\.?\s+[A-Z]",  # 以 Dr. 开头
            r"^Prof\.?\s+[A-Z]",  # 以 Prof. 开头
            # 新增：扩展人名格式
            r"^[A-Z][a-z]+[A-Z][a-z]+$",  # 拼音人名（如 "TingnanZhang"）
            r"^[A-Z][a-z]+-[A-Z][a-z]+\s+[A-Z][a-z]+$",  # 连字符名（如 "Anna-Luisa Brakman"）
            r"^[A-Z][a-z]+\s+[A-Z]\s+[A-Z][a-z]+$",  # 中间名单字母（如 "Kelly Y Chen"）
            r"^[A-Z][a-z]+\s+[A-Z][a-z]+-[A-Z][a-z]+$",  # 姓有连字符（如 "John Smith-Jones"）
            r"^[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+$",  # 双缩写（如 "J. K. Rowling"）
            r"^[A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+-[A-Z][a-z]+$",  # 三词+连字符
        ],
        description_patterns=[
            # 描述中的人物指示模式（优先级最高）
            r"\bis\s+a\s+researcher\b",
            r"\bis\s+a\s+professor\b",
            r"\bis\s+a\s+scientist\b",
            r"\bis\s+a\s+student\b",
            r"\bis\s+a\s+engineer\b",
            r"\bis\s+a\s+developer\b",
            r"\bis\s+a\s+member\b",
            r"\bis\s+a\s+leader\b",
            r"\bis\s+a\s+director\b",
            r"\bis\s+a\s+founder\b",
            r"\bis\s+an?\s+(?:AI|ML)\s+researcher\b",
            r"\bworks?\s+(?:on|at|in|for)\b",  # X works on/at/in/for ...
            r"\binvolved\s+in\b",  # X is involved in ...
            r"\bworking\s+on\b",  # X is working on ...
            r"\bcontributed\s+to\b",  # X contributed to ...
            r"\bauthored\b",  # X authored ...
            r"\bpublished\b",  # X published ...
        ],
        priority=1  # 最高优先级 - 确保描述模式"is a researcher"优先匹配人物
    ),
    
    # 组织/机构类型
    SemanticTypeConfig(
        name="组织",
        keywords=[
            "university", "college", "institute", "institution", "school",
            "laboratory", "lab", "center", "centre", "department", "faculty",
            "company", "corporation", "inc", "ltd", "llc", "org",
            "google", "microsoft", "meta", "openai", "deepmind", "nvidia",
            "amazon", "apple", "facebook", "baidu", "alibaba", "tencent",
            "research group", "consortium", "foundation", "association",
        ],
        patterns=[
            r"(?i)^.*(university|institute|laboratory|inc\.|ltd\.|llc).*$",
        ],
        priority=20
    ),
    
    # 技术/方法类型 - 提高优先级，在模型之前
    SemanticTypeConfig(
        name="技术/方法",
        keywords=[
            "algorithm", "method", "technique", "approach",
            "architecture", "mechanism", "strategy", "optimization",
            "learning", "training", "inference", "prediction",
            "classification", "detection", "segmentation", "generation",
            "reinforcement learning", "supervised learning", "unsupervised", "self-supervised",
            "fine-tuning", "pre-training", "transfer learning",
            "backpropagation", "gradient descent", "regularization",
            "dropout", "batch normalization", "layer normalization",
            "convolution", "pooling", "attention mechanism",
            "loss function", "activation function", "objective",
            "retrieval", "augmentation", "preprocessing",
            "rag", "retrieval-augmented", "chain-of-thought", "cot",
            "prompt", "prompting", "in-context learning",
            "imitation learning", "robot learning", "policy learning",
            "zero-shot", "few-shot", "multi-task",
        ],
        patterns=[
            r"(?i)^.*(algorithm|method|technique|approach).*$",
            r"(?i).*learning$",  # 以 learning 结尾的通常是方法
        ],
        priority=25
    ),
    
    # 模型类型
    SemanticTypeConfig(
        name="模型",
        keywords=[
            "model", "neural network", "transformer", "bert", "gpt",
            "llm", "language model", "vision model", "diffusion model",
            "encoder", "decoder", "attention", "embedding model",
            "classifier model", "detector model", "generator", "discriminator",
            "vit", "resnet", "vgg", "efficientnet", "yolo",
            "llama", "claude", "gemini", "qwen", "chatgpt", "palm",
            "stable diffusion", "dall-e", "midjourney",
            "foundation model", "pretrained model",
        ],
        patterns=[
            r"(?i)^(gpt|bert|t5|llama|claude|gemini|qwen|palm|falcon|mistral|phi)-?\d*",
            r"(?i)^.*(model|transformer|network)$",  # 以 model/transformer/network 结尾
        ],
        priority=30
    ),
    
    # 评估指标类型
    SemanticTypeConfig(
        name="评估指标",
        keywords=[
            "accuracy", "precision", "recall", "f1", "f1-score",
            "loss", "error rate", "perplexity", "bleu", "rouge",
            "metric", "measure", "score", "evaluation",
            "performance", "sota", "state-of-the-art",
            "auc", "roc", "map", "iou", "dice",
        ],
        patterns=[
            r"(?i)^(accuracy|precision|recall|f1|bleu|rouge|perplexity)$",
        ],
        priority=40
    ),
    
    # 任务类型
    SemanticTypeConfig(
        name="任务",
        keywords=[
            "task", "problem", "challenge", "application",
            "nlp", "natural language processing", "computer vision",
            "speech recognition", "machine translation", "summarization",
            "question answering", "qa", "text generation",
            "image classification", "object detection", "semantic segmentation",
            "robot manipulation", "navigation", "planning",
            "reasoning", "dialogue", "conversation",
        ],
        patterns=[
            r"(?i)^.*(task|problem|challenge).*$",
        ],
        priority=50
    ),
    
    # 概念类型
    SemanticTypeConfig(
        name="概念",
        keywords=[
            "concept", "theory", "principle", "idea", "notion",
            "property", "characteristic", "feature", "attribute",
            "representation", "abstraction", "paradigm",
            "hypothesis", "assumption", "constraint",
            "scalability", "efficiency", "robustness", "generalization",
        ],
        patterns=[],
        priority=60
    ),
    
    # 工具/系统类型
    SemanticTypeConfig(
        name="工具/系统",
        keywords=[
            "system", "tool", "platform", "software", "library", "framework",
            "api", "sdk", "interface", "pipeline", "workflow",
            "pytorch", "tensorflow", "keras", "jax", "huggingface",
            "langchain", "llamaindex", "openai api",
            "cuda", "gpu", "tpu", "hardware",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "simulator", "environment", "robot",
        ],
        patterns=[
            r"(?i)^.*(system|tool|platform|library|api|framework).*$",
        ],
        priority=70
    ),
    
    # 论文/研究类型 - 添加描述模式以识别论文
    SemanticTypeConfig(
        name="研究工作",
        keywords=[
            "paper", "publication", "article", "study", "research",
            "contribution", "finding", "experiment",
            "ieee", "acl", "neurips", "icml", "iclr", "cvpr", "iccv",
            "arxiv", "journal", "conference", "workshop",
        ],
        patterns=[
            r"(?i)^\d{4}\s+ieee",  # 年份 + IEEE
            r"(?i)^(arxiv|doi):",
        ],
        description_patterns=[
            # 描述中的论文/研究指示模式
            r"\bauthors?\s+of\s+(?:a\s+)?(?:the\s+)?paper\b",  # authors of a paper
            r"\bpublished\s+(?:in|at|by)\b",  # published in/at/by
            r"\bpaper\s+(?:on|about|titled)\b",  # paper on/about/titled
            r"\bis\s+(?:a|the)\s+paper\b",  # is a paper
            r"\bis\s+(?:a|the)\s+publication\b",  # is a publication
            r"\bpresented\s+(?:at|in)\b",  # presented at/in
            r"\bappears?\s+in\b",  # appears in
            r"\baccepted\s+(?:at|by|to)\b",  # accepted at/by/to
        ],
        priority=4  # 提高优先级，使描述模式能够更早匹配
    ),
]


class NodeTypeClassifier:
    """节点类型分类器"""
    
    def __init__(self, configs: Optional[List[SemanticTypeConfig]] = None):
        """
        初始化分类器
        
        Args:
            configs: 语义类型配置列表，如果为None则使用默认配置
        """
        self.configs = configs or SEMANTIC_TYPE_CONFIGS
        # 按优先级排序
        self.configs = sorted(self.configs, key=lambda x: x.priority)
        # 预编译正则表达式
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()
        
        logger.info(f"NodeTypeClassifier initialized with {len(self.configs)} semantic types")
    
    def _compile_patterns(self) -> None:
        """预编译所有正则表达式（包括实体名模式和描述模式）"""
        self._compiled_patterns = {}
        self._compiled_desc_patterns: Dict[str, List[re.Pattern]] = {}
        
        for config in self.configs:
            # 编译实体名模式
            self._compiled_patterns[config.name] = []
            for pattern in config.patterns:
                try:
                    # 人物类型的正则需要区分大小写（用于匹配人名格式）
                    # 其他类型使用 IGNORECASE 便于匹配
                    flags = 0 if config.name == "人物" else re.IGNORECASE
                    self._compiled_patterns[config.name].append(
                        re.compile(pattern, flags)
                    )
                except re.error as e:
                    logger.warning(f"Invalid regex pattern '{pattern}' for type '{config.name}': {e}")
            
            # 编译描述模式
            self._compiled_desc_patterns[config.name] = []
            for pattern in config.description_patterns:
                try:
                    self._compiled_desc_patterns[config.name].append(
                        re.compile(pattern, re.IGNORECASE)
                    )
                except re.error as e:
                    logger.warning(f"Invalid description pattern '{pattern}' for type '{config.name}': {e}")
    
    def classify(self, node: Dict[str, Any]) -> str:
        """
        对节点进行语义类型分类
        
        分类优先级（从高到低）：
        1. 描述模式匹配 - 检测如 "is a researcher" 等语义模式
        2. 实体名正则匹配 - 匹配人名、模型名等精确格式
        3. 关键词匹配 - 匹配实体名和描述中的关键词
        4. 标签匹配 - 检查现有标签
        
        Args:
            node: 节点字典，包含 id, labels, properties
            
        Returns:
            str: 语义类型名称
        """
        # 提取节点信息
        entity_id = node.get('properties', {}).get('entity_id', node.get('id', '')) or ''
        description = node.get('properties', {}).get('description', '') or ''
        labels = node.get('labels', []) or []
        
        entity_lower = entity_id.lower()
        desc_lower = description.lower()
        
        # 技术术语和组织名称排除列表（这些词不应被匹配为人名）
        tech_term_exclusions = {
            # 技术术语
            'learning', 'training', 'model', 'network', 'algorithm', 'method',
            'system', 'robot', 'manipulation', 'navigation', 'planning', 'control',
            'detection', 'recognition', 'segmentation', 'generation', 'classification',
            'processing', 'analysis', 'optimization', 'inference', 'prediction',
            'architecture', 'framework', 'mechanism', 'strategy', 'policy',
            'transformer', 'attention', 'embedding', 'encoder', 'decoder',
            'reinforcement', 'supervised', 'unsupervised', 'self-supervised',
            'fine-tuning', 'pre-training', 'transfer', 'multi-task', 'zero-shot',
            'dataset', 'benchmark', 'corpus', 'evaluation', 'metric',
            # 组织/机构相关词汇
            'university', 'college', 'institute', 'institution', 'school',
            'laboratory', 'lab', 'center', 'centre', 'department', 'faculty',
            'company', 'corporation', 'inc', 'ltd', 'llc', 'org',
            'research', 'foundation', 'association', 'consortium', 'group',
        }
        
        # 检查实体名称是否包含技术术语（用于跳过人名正则匹配）
        entity_words = set(entity_lower.split())
        contains_tech_term = bool(entity_words & tech_term_exclusions)
        
        # =========================================================
        # 阶段 1：描述模式匹配（最高优先级）
        # 检测描述中的语义模式，如 "is a researcher"
        # =========================================================
        for config in self.configs:
            for pattern in self._compiled_desc_patterns.get(config.name, []):
                if pattern.search(description):
                    logger.debug(f"Node '{entity_id}' classified as '{config.name}' by description pattern")
                    return config.name
        
        # =========================================================
        # 阶段 2：实体名正则匹配
        # 匹配人名、模型名等精确格式
        # =========================================================
        for config in self.configs:
            for pattern in self._compiled_patterns.get(config.name, []):
                # 对于人物类型，如果实体名包含技术术语则跳过
                if config.name == "人物" and contains_tech_term:
                    continue
                if pattern.search(entity_id):
                    logger.debug(f"Node '{entity_id}' classified as '{config.name}' by entity pattern")
                    return config.name
        
        # =========================================================
        # 阶段 3：关键词匹配
        # 匹配实体名中的关键词（仅实体名，不再合并描述）
        # =========================================================
        for config in self.configs:
            for keyword in config.keywords:
                keyword_lower = keyword.lower()
                # 只匹配实体名，避免描述中的技术术语触发误分类
                if keyword_lower in entity_lower:
                    logger.debug(f"Node '{entity_id}' classified as '{config.name}' by keyword '{keyword}'")
                    return config.name
        
        # =========================================================
        # 阶段 4：标签匹配
        # 检查现有标签（可能包含类型信息）
        # =========================================================
        for config in self.configs:
            for label in labels:
                label_lower = label.lower()
                for keyword in config.keywords:
                    if keyword.lower() in label_lower:
                        logger.debug(f"Node '{entity_id}' classified as '{config.name}' by label '{label}'")
                        return config.name
        
        # 未匹配到任何类型，返回默认值
        return "其他"
    
    def classify_batch(self, nodes: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        批量分类节点
        
        Args:
            nodes: 节点字典列表
            
        Returns:
            Dict[str, str]: 节点ID到语义类型的映射
        """
        result = {}
        type_counts: Dict[str, int] = {}
        
        for node in nodes:
            node_id = node.get('id', '')
            semantic_type = self.classify(node)
            result[node_id] = semantic_type
            type_counts[semantic_type] = type_counts.get(semantic_type, 0) + 1
        
        logger.info(f"Batch classification complete: {len(nodes)} nodes, distribution: {type_counts}")
        return result
    
    def get_available_types(self) -> List[str]:
        """获取所有可用的语义类型名称"""
        return [config.name for config in self.configs] + ["其他"]


# 单例实例，避免重复初始化
_classifier_instance: Optional[NodeTypeClassifier] = None


def get_classifier() -> NodeTypeClassifier:
    """获取分类器单例实例"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = NodeTypeClassifier()
    return _classifier_instance
