#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节点类型分类器测试

测试新的分类逻辑：描述模式优先、增强人名正则等。
"""

import pytest
from backend.service.node_type_classifier import (
    NodeTypeClassifier,
    get_classifier,
    SemanticTypeConfig,
    SEMANTIC_TYPE_CONFIGS
)


# ==================== 测试数据工厂 ====================

def create_test_node(
    entity_id: str,
    description: str = "",
    labels: list = None
) -> dict:
    """创建测试节点字典"""
    return {
        'id': entity_id,
        'labels': labels or ['Entity'],
        'properties': {
            'entity_id': entity_id,
            'description': description
        }
    }


# ==================== 描述模式匹配测试 ====================

class TestDescriptionPatternMatching:
    """描述模式匹配测试 - 最高优先级"""
    
    def test_classify_researcher_by_description(self):
        """测试通过描述识别研究人员"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='TingnanZhang',
            description='TingnanZhang is a researcher involved in robotics and machine learning applications.'
        )
        assert classifier.classify(node) == '人物'
    
    def test_classify_professor_by_description(self):
        """测试通过描述识别教授"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='John Smith',
            description='John Smith is a professor at MIT working on AI research.'
        )
        assert classifier.classify(node) == '人物'
    
    def test_classify_scientist_by_description(self):
        """测试通过描述识别科学家"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='Anna-Luisa Brakman',
            description='Anna-Luisa Brakman is a scientist involved in AI and machine learning.'
        )
        assert classifier.classify(node) == '人物'
    
    def test_classify_student_by_description(self):
        """测试通过描述识别学生"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='Kelly Y Chen',
            description='Kelly Y Chen is a student working on the Mosaic system.'
        )
        assert classifier.classify(node) == '人物'
    
    def test_classify_person_works_on(self):
        """测试 'works on' 模式"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='SomeName',
            description='SomeName works on robot manipulation tasks.'
        )
        assert classifier.classify(node) == '人物'
    
    def test_classify_person_involved_in(self):
        """测试 'involved in' 模式"""
        classifier = get_classifier()
        node = create_test_node(
            entity_id='TestPerson',
            description='TestPerson is involved in deep learning research.'
        )
        assert classifier.classify(node) == '人物'


# ==================== 人名正则匹配测试 ====================

class TestPersonNamePatterns:
    """人名正则匹配测试"""
    
    def test_classify_pinyin_name(self):
        """测试拼音人名（无空格）"""
        classifier = get_classifier()
        # 仅使用人名，无描述
        node = create_test_node(entity_id='TingnanZhang', description='A contributor to the project.')
        result = classifier.classify(node)
        # 如果描述无明确人物指示，应通过人名正则匹配
        # 由于描述不包含人物模式，应该依赖正则
        assert result == '人物'
    
    def test_classify_hyphenated_first_name(self):
        """测试连字符名（如 Anna-Luisa Brakman）"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Anna-Luisa Brakman', description='A contributor.')
        assert classifier.classify(node) == '人物'
    
    def test_classify_middle_initial_name(self):
        """测试中间名单字母（如 Kelly Y Chen）"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Kelly Y Chen', description='A contributor.')
        assert classifier.classify(node) == '人物'
    
    def test_classify_standard_two_word_name(self):
        """测试标准两词人名"""
        classifier = get_classifier()
        node = create_test_node(entity_id='John Smith', description='Unknown entity.')
        assert classifier.classify(node) == '人物'
    
    def test_classify_three_word_name(self):
        """测试三词人名"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Mary Jane Watson', description='Unknown entity.')
        assert classifier.classify(node) == '人物'
    
    def test_classify_dr_prefix(self):
        """测试 Dr. 前缀"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Dr. Alan Turing', description='Unknown entity.')
        assert classifier.classify(node) == '人物'


# ==================== 技术术语排除测试 ====================

class TestTechTermExclusion:
    """技术术语不应被误判为人名"""
    
    def test_machine_learning_not_person(self):
        """Machine Learning 不应被判为人物"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Machine Learning', description='A field of study.')
        result = classifier.classify(node)
        assert result != '人物'
    
    def test_reinforcement_learning_not_person(self):
        """Reinforcement Learning 不应被判为人物"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Reinforcement Learning', description='A type of learning.')
        result = classifier.classify(node)
        assert result == '技术/方法'
    
    def test_robot_manipulation_not_person(self):
        """Robot Manipulation 不应被判为人物"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Robot Manipulation', description='A robotic task.')
        result = classifier.classify(node)
        assert result != '人物'


# ==================== 其他类型测试 ====================

class TestOtherTypes:
    """其他类型分类测试"""
    
    def test_classify_dataset(self):
        """测试数据集分类"""
        classifier = get_classifier()
        node = create_test_node(entity_id='ImageNet', description='A large image dataset.')
        assert classifier.classify(node) == '数据集'
    
    def test_classify_model(self):
        """测试模型分类"""
        classifier = get_classifier()
        node = create_test_node(entity_id='GPT-4', description='A large language model.')
        # GPT-4 应该匹配模型正则
        assert classifier.classify(node) == '模型'
    
    def test_classify_organization(self):
        """测试组织分类"""
        classifier = get_classifier()
        node = create_test_node(entity_id='Stanford University', description='A research university.')
        assert classifier.classify(node) == '组织'


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_description(self):
        """测试空描述"""
        classifier = get_classifier()
        node = create_test_node(entity_id='John Smith', description='')
        # 应该通过人名正则匹配
        assert classifier.classify(node) == '人物'
    
    def test_unknown_entity(self):
        """测试未知实体"""
        classifier = get_classifier()
        node = create_test_node(entity_id='XYZ123', description='Some random text.')
        result = classifier.classify(node)
        assert result == '其他'
    
    def test_classifier_singleton(self):
        """测试分类器单例"""
        c1 = get_classifier()
        c2 = get_classifier()
        assert c1 is c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
