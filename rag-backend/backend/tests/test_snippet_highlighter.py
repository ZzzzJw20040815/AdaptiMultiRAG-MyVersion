#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""snippet_highlighter 单元测试"""

from backend.rag.chunks.snippet_highlighter import extract_highlight, extract_highlight_candidates


def test_extract_highlight_strips_sticky_title_front_matter():
    query = "3D-VLA这篇文献的主要内容是什么"
    content = (
        "3D-VLA: A 3D Vision-Language-Action Generative World Model"
        "Haoyu Zhen1 2Xiaowen Qiu1Peihao Chen3Jincheng Yang2Xin Yan4"
        "Yilun Du5Yining Hong6Chuang Gan17https://vis-www.cs. umass. edu/3dvla"
        "AbstractRecent vision-language-action (VLA) models rely on 2D inputs, "
        "lacking integration with the broader realm of the 3D physical world."
    )

    highlight = extract_highlight(content, query)
    low = highlight.lower()

    assert low.startswith("abstract")
    assert "haoyu zhen" not in low
    assert "vision-language-action (vla) models rely on 2d inputs" in low


def test_extract_highlight_candidates_prefers_summary_sentences_for_summary_question():
    query = "这篇文献的主要内容和核心贡献是什么"
    content = (
        "Abstract: We propose a 3D vision-language-action generative world model that connects perception, reasoning, and action. "
        "The architecture introduces interaction tokens and diffusion alignment for embodied tasks. "
        "On benchmark datasets, the model improves PSNR by 14.41 and reaches 0.909 SSIM."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) >= 1
    assert "we propose" in candidates[0]["text"].lower()


def test_extract_highlight_candidates_prefers_metric_sentences_for_experiment_question():
    query = "这篇文献的实验结果和性能指标如何"
    content = (
        "Abstract: We propose a 3D vision-language-action generative world model that connects perception, reasoning, and action. "
        "The architecture introduces interaction tokens and diffusion alignment for embodied tasks. "
        "On benchmark datasets, the model improves PSNR by 14.41 and reaches 0.909 SSIM."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) >= 1
    assert "psnr" in candidates[0]["text"].lower() or "ssim" in candidates[0]["text"].lower()


def test_extract_highlight_candidates_trims_conference_header_noise():
    query = "这篇文献的主要内容是什么"
    content = (
        "CVPR 14 Mar 2024 3D-VLA: A 3D Vision-Language-Action Generative World Model "
        "What should I do next? To this end, we propose 3D-VLA by introducing a new family "
        "of embodied foundation models that seamlessly link 3D perception, reasoning, and action."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=1)

    assert len(candidates) == 1
    assert candidates[0]["text"].lower().startswith("to this end")
    assert "cvpr" not in candidates[0]["text"].lower()
    assert "what should i do next" not in candidates[0]["text"].lower()


def test_extract_highlight_candidates_prefers_natural_language_result_over_table_row():
    query = "这篇文献的实验结果和性能表现怎么样"
    content = (
        "Methods IoU Acc@25 Acc@50 Kosmos 2 10.92 12.73 3.85 CoVLM 19.81 25.39 16.61 3D-VLA 29.33 42.26 27.09. "
        "In Tables 1, 3D-VLA outperforms all 2D VLM methods on language reasoning tasks, "
        "which provides more accurate spatial information for reasoning."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=1)

    assert len(candidates) == 1
    assert "outperforms" in candidates[0]["text"].lower()
    assert "kosmos" not in candidates[0]["text"].lower()


def test_extract_highlight_candidates_keeps_best_evidence_first():
    query = "这篇文献的实验结果和性能表现怎么样"
    content = (
        "Abstract: We propose a 3D vision-language-action generative world model that connects perception, reasoning, and action. "
        "The architecture introduces interaction tokens and diffusion alignment for embodied tasks. "
        "Experiments show that 3D-VLA outperforms baseline methods on language reasoning tasks."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) >= 1
    assert "outperforms" in candidates[0]["text"].lower()
    assert candidates[0]["label"] == "实验结论"


def test_extract_highlight_candidates_marks_motivation_sentence():
    query = "这篇文献的主要内容和研究动机是什么"
    content = (
        "Abstract Recent vision-language-action (VLA) models rely on 2D inputs, lacking integration with the broader realm of the 3D physical world. "
        "To this end, we propose 3D-VLA by introducing a new family of embodied foundation models that seamlessly link 3D perception, reasoning, and action. "
        "Specifically, we build our 3D-VLA on top of a 3D large language model to equip the model with 3D understanding ability."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)
    motivation = next(candidate for candidate in candidates if "lacking integration" in candidate["text"].lower())

    assert motivation["label"] == "研究动机"
    assert motivation["role"] == "motivation"


def test_extract_highlight_candidates_strip_numeric_prefix_from_sentence():
    query = "这篇文献的方法是什么"
    content = (
        "2) held-in evaluation where we train the released model on 2D-image-action-language pairs. "
        "We utilize our curated 3D-language video data to train a conditional diffusion model that edits the initial state modality based on instructions. "
        "These interaction tokens are designed to inform the decoder about the type of tasks."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) >= 1
    assert all(not candidate["text"].startswith("2)") for candidate in candidates)



def test_extract_highlight_candidates_demotes_experiment_setup_for_method_question():
    query = "这篇文献的方法架构和关键设计是什么"
    content = (
        "2) held-in evaluation where we train the released model on 2D-image-action-language pairs. "
        "We utilize our curated 3D-language video data to train a conditional diffusion model that edits the initial state modality based on instructions. "
        "These interaction tokens are designed to inform the decoder about the type of tasks."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) == 2
    assert candidates[0]["text"].lower().startswith("we utilize")
    assert all("held-in evaluation" not in candidate["text"].lower() for candidate in candidates)


def test_extract_highlight_candidates_filters_section_heading_like_sentence():
    query = "这篇文献的主要内容和核心贡献是什么"
    content = (
        "3D Reasoning and LocalizationTasks. "
        "In this section, we evaluate 3D-VLA in three aspects: 3D reasoning and localization, "
        "multi-modal goal generation, and embodied action planning."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) == 1
    assert "localization tasks" not in candidates[0]["text"].lower()
    assert candidates[0]["text"].lower().startswith("in this section")


def test_extract_highlight_candidates_filters_task_list_noise_when_good_sentence_exists():
    query = "这篇文献的主要内容和核心贡献是什么"
    content = (
        "Embodied Question AnsweringDetect the knife with 3D B-box. "
        "Object DetectionWhat-if Question AnsweringDescribe the task with 3D B-box. "
        "To this end, we propose 3D-VLA by introducing a new family of embodied foundation models "
        "that seamlessly link 3D perception, reasoning, and action through a generative world model."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=2)

    assert len(candidates) >= 1
    assert candidates[0]["text"].lower().startswith("to this end")
    assert all("detect the knife" not in candidate["text"].lower() for candidate in candidates)


def test_extract_highlight_candidates_drops_truncated_citation_tail_for_method_question():
    query = "这篇文献的方法架构和关键设计是什么"
    content = (
        ", 2023) to equipthe model with 3D understanding ability. "
        "Since embodied tasks could not be accomplished via language generation solely and require "
        "deeper digging into the dynamic scenes, we add special interactive tokens to the LLM vocabulary."
    )

    candidates = extract_highlight_candidates(content, query, max_candidates=1)

    assert len(candidates) == 1
    assert candidates[0]["text"].lower().startswith("since embodied tasks")
    assert "equipthe" not in candidates[0]["text"].lower()


def test_extract_highlight_short_text_uses_cleaned_candidates_instead_of_raw_chunk():
    query = "这篇文献的方法架构和关键设计是什么"
    content = (
        ", 2023) to equipthe model with 3D understanding ability. "
        "Since embodied tasks could not be accomplished via language generation solely and require deeper digging into the dynamic scenes, "
        "we add special interactive tokens to the LLM vocabulary."
    )

    highlight = extract_highlight(content, query, max_sentences=1)

    assert highlight.lower().startswith("since embodied tasks")
    assert "equipthe" not in highlight.lower()
