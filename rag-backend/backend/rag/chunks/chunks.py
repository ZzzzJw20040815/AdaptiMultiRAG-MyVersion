from typing import List, Optional, Any, Union

from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document

from .models import ChunkStrategy, ChunkConfig, ChunkResult, DocumentContent


class TextChunker:
    """文本分块处理器
    
    支持多种分块策略：
    1. 字符级分块 - 按指定字符数分割
    2. 语义分块 - 基于语义相似度分割
    3. 递归分块 - 按分隔符优先级递归分割
    4. Markdown标题分块 - 按Markdown标题结构分割
    
    PR-5 增强: 为每个分块添加溯源元数据
    """
    
    def __init__(self, embeddings_model: Optional[Embeddings] = None):
        """初始化分块器
        
        Args:
            embeddings_model: 嵌入模型，语义分块时必需
        """
        self.embeddings_model = embeddings_model
    
    def chunk_document(self, document: DocumentContent, config: ChunkConfig) -> ChunkResult:
        """对文档进行分块处理
        
        Args:
            document: 文档内容对象
            config: 分块配置
            
        Returns:
            ChunkResult: 分块结果对象
        """
        if not document.content or not document.content.strip():
            return ChunkResult(
                chunks=[],
                strategy=config.strategy,
                total_chunks=0,
                document_name=document.document_name,
                doc_id=document.doc_id,
                source_url=document.source_url
            )
        
        try:
            if config.strategy == ChunkStrategy.CHARACTER:
                result = self._character_chunk(document.content, config, document.document_name)
            elif config.strategy == ChunkStrategy.SEMANTIC:
                result = self._semantic_chunk(document.content, config, document.document_name)
            elif config.strategy == ChunkStrategy.RECURSIVE:
                result = self._recursive_chunk(document.content, config, document.document_name)
            elif config.strategy == ChunkStrategy.MARKDOWN_HEADER:
                result = self._markdown_header_chunk(document.content, config, document.document_name)
            else:
                return ChunkResult(
                    chunks=[],
                    strategy=config.strategy,
                    total_chunks=0,
                    document_name=document.document_name,
                    doc_id=document.doc_id,
                    source_url=document.source_url
                )
            
            # PR-5: 添加溯源元数据到每个分块
            if config.add_source_metadata and result.chunks:
                result = self._enrich_chunks_metadata(
                    result, 
                    document, 
                    config
                )
            
            # 设置结果的 doc_id 和 source_url
            result.doc_id = document.doc_id
            result.source_url = document.source_url
            
            return result
                
        except Exception as e:
            return ChunkResult(
                chunks=[],
                strategy=config.strategy,
                total_chunks=0,
                document_name=document.document_name,
                doc_id=document.doc_id,
                source_url=document.source_url
            )
    
    def _enrich_chunks_metadata(
        self, 
        result: ChunkResult, 
        document: DocumentContent, 
        config: ChunkConfig
    ) -> ChunkResult:
        """
        为分块添加溯源元数据 (PR-5)
        
        Args:
            result: 原始分块结果
            document: 文档内容
            config: 分块配置
            
        Returns:
            ChunkResult: 增强后的分块结果
        """
        from datetime import datetime
        
        original_text = document.content
        total_chunks = len(result.chunks)
        
        enriched_chunks = []
        current_pos = 0
        
        for idx, chunk in enumerate(result.chunks):
            chunk_text = chunk.page_content
            
            # 计算字符范围
            char_start = original_text.find(chunk_text, current_pos)
            if char_start == -1:
                # 如果找不到（可能有重叠），从头开始找
                char_start = original_text.find(chunk_text)
            
            char_end = char_start + len(chunk_text) if char_start != -1 else None
            
            # 更新搜索位置（考虑重叠）
            if char_start != -1:
                current_pos = max(current_pos, char_start + 1)
            
            # 提取或保留已有的章节信息
            section = chunk.metadata.get('section') or chunk.metadata.get('Header_1') or chunk.metadata.get('Header_2')
            section_hierarchy = []
            for i in range(1, 7):
                header_key = f'Header_{i}'
                if header_key in chunk.metadata and chunk.metadata[header_key]:
                    section_hierarchy.append(chunk.metadata[header_key])
            
            # 构建增强的元数据
            enhanced_metadata = {
                # 文档标识
                'doc_id': document.doc_id,
                'doc_name': document.document_name,
                'source_url': document.source_url,
                
                # 位置信息
                'char_start': char_start if char_start != -1 else None,
                'char_end': char_end,
                
                # 分块信息
                'chunk_index': idx,
                'total_chunks': total_chunks,
                
                # 章节信息 (如果有)
                'section': section,
                'section_hierarchy': section_hierarchy if section_hierarchy else None,
                
                # 时间戳
                'created_at': datetime.now().isoformat(),
            }
            
            # 合并原有的元数据（保留 Header_X 等）
            final_metadata = {**chunk.metadata, **{k: v for k, v in enhanced_metadata.items() if v is not None}}
            
            enriched_chunks.append(Document(
                page_content=chunk_text,
                metadata=final_metadata
            ))
        
        result.chunks = enriched_chunks
        return result
    
    def _character_chunk(self, text: str, config: ChunkConfig, document_name: str) -> ChunkResult:
        """字符级分块"""
        text_splitter = CharacterTextSplitter(
            separator=config.separator,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            is_separator_regex=config.is_separator_regex,
        )
        
        chunks = text_splitter.create_documents([text])
        
        # PR-5: 不再清空 metadata，保留后续填充
        
        return ChunkResult(
            chunks=chunks,
            strategy=config.strategy,
            total_chunks=len(chunks),
            document_name=document_name
        )
    
    def _semantic_chunk(self, text: str, config: ChunkConfig, document_name: str) -> ChunkResult:
        """语义分块"""
        if self.embeddings_model is None:
            return ChunkResult(
                chunks=[],
                strategy=config.strategy,
                total_chunks=0,
                document_name=document_name
            )
        
        semantic_chunker = SemanticChunker(
            embeddings=self.embeddings_model,
            breakpoint_threshold_type=config.breakpoint_threshold_type,
            breakpoint_threshold_amount=config.breakpoint_threshold_amount,
            sentence_split_regex=config.sentence_split_regex,
        )
        
        # 如果设置了最小分块大小
        if config.min_chunk_size:
            semantic_chunker.min_chunk_size = config.min_chunk_size
        
        chunks = semantic_chunker.create_documents([text])
        
        # PR-5: 不再清空 metadata，保留后续填充
        
        return ChunkResult(
            chunks=chunks,
            strategy=config.strategy,
            total_chunks=len(chunks),
            document_name=document_name
        )
    
    def _recursive_chunk(self, text: str, config: ChunkConfig, document_name: str) -> ChunkResult:
        """递归分块"""
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
            separators=config.separators
        )
        
        chunks = recursive_splitter.create_documents([text])
        
        # PR-5: 不再清空 metadata，保留后续填充
        
        return ChunkResult(
            chunks=chunks,
            strategy=config.strategy,
            total_chunks=len(chunks),
            document_name=document_name
        )
    
    def _markdown_header_chunk(self, text: str, config: ChunkConfig, document_name: str) -> ChunkResult:
        """Markdown标题分块"""
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=config.headers_to_split_on
        )
        
        chunks = markdown_splitter.split_text(text)
        
        # 转换为Document对象，保留 Header 元数据 (PR-5)
        if isinstance(chunks, list) and chunks:
            if isinstance(chunks[0], Document):
                # 保留所有 Document 的原始 metadata（包含 Header_X）
                documents = chunks
            else:
                # 如果是字符串列表，转换为 Document
                documents = [Document(page_content=chunk, metadata={}) for chunk in chunks]
        else:
            documents = []
        
        return ChunkResult(
            chunks=documents,
            strategy=config.strategy,
            total_chunks=len(documents),
            document_name=document_name
        )
    
    def chunk_with_strategy(self, text: str, strategy: Union[str, ChunkStrategy], 
                           document_name: str = "", **kwargs) -> ChunkResult:
        """便捷的分块方法
        
        Args:
            text: 待分块的文本
            strategy: 分块策略
            **kwargs: 分块参数
            
        Returns:
            ChunkResult: 分块结果
        """
        if isinstance(strategy, str):
            try:
                strategy = ChunkStrategy(strategy)
            except ValueError:
                return ChunkResult(
                    chunks=[],
                    strategy=ChunkStrategy.CHARACTER,
                    total_chunks=0,
                    document_name=document_name
                )
        
        config = ChunkConfig(strategy=strategy, **kwargs)
        document = DocumentContent(content=text, document_name=document_name)
        return self.chunk_document(document, config)


# 使用示例
if __name__ == "__main__":

    
    # 示例文本
    sample_text = """
    # 人工智能简介
    
    人工智能（Artificial Intelligence，AI）是计算机科学的一个分支。它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。
    
    ## 发展历史
    
    人工智能的研究历史已有数十年。从1956年的达特茅斯会议开始，人工智能正式成为一门学科。
    
    ### 早期发展
    
    早期的人工智能研究主要集中在逻辑推理和专家系统上。研究者们试图通过编写规则来模拟人类的推理过程。
    
    ### 现代发展
    
    随着机器学习和深度学习技术的发展，人工智能取得了突破性进展。特别是在图像识别、自然语言处理和游戏AI等领域。
    
    ## 应用领域
    
    人工智能目前在多个领域都有广泛应用：医疗诊断、自动驾驶、智能推荐系统等。这些应用正在改变我们的生活方式。
    """
    
    # 创建分块器（不使用嵌入模型进行基本测试）
    chunker = TextChunker()
    
    print("=== 字符级分块测试 ===")
    char_config = ChunkConfig(
        strategy=ChunkStrategy.CHARACTER,
        chunk_size=50,
        chunk_overlap=10,
        separator=""
    )
    char_result = chunker.chunk_document(DocumentContent(content=sample_text, document_name="test.txt"), char_config)
    print(f"总块数: {char_result.total_chunks}")
    print(char_result)
    # if char_result.chunks:
    #     print(f"第一块内容: {char_result.chunks[0].page_content[:100]}...")
    
    # print("\n=== 递归分块测试 ===")
    # recursive_config = ChunkConfig(
    #     strategy=ChunkStrategy.RECURSIVE,
    #     chunk_size=100,
    #     chunk_overlap=20
    # )
    # recursive_result = chunker.chunk_text(sample_text, recursive_config)
    # print(f"成功: {recursive_result.success}")
    # print(f"总块数: {recursive_result.total_chunks}")
    # if recursive_result.chunks:
    #     print(f"第一块内容: {recursive_result.chunks[0].page_content[:100]}...")
    
    # print("\n=== Markdown标题分块测试 ===")
    # md_config = ChunkConfig(
    #     strategy=ChunkStrategy.MARKDOWN_HEADER
    # )
    # md_result = chunker.chunk_text(sample_text, md_config)
    # print(f"成功: {md_result.success}")
    # print(f"总块数: {md_result.total_chunks}")
    # if md_result.chunks:
    #     print(f"第一块内容: {md_result.chunks[0].page_content[:100]}...")
    
    # print("\n=== 便捷方法测试 ===")
    # quick_result = chunker.chunk_with_strategy(
    #     sample_text, 
    #     "recursive",
    #     chunk_size=150,
    #     chunk_overlap=30
    # )
    # print(f"成功: {quick_result.success}")
    # print(f"总块数: {quick_result.total_chunks}")
    
    # # 测试语义分块（需要嵌入模型）
    # print("\n=== 语义分块测试（需要嵌入模型）===")
    # try:
    #     # 注意：这里需要先注册嵌入模型提供商
    #     # register_embeddings_provider("openai", "openai")  
    #     # embeddings_model = load_embeddings("openai:text-embedding-ada-002")
        
    #     # 这里使用None模型测试错误处理
    #     semantic_config = ChunkConfig(
    #         strategy=ChunkStrategy.SEMANTIC,
    #         breakpoint_threshold_amount=90
    #     )
    #     semantic_result = chunker.chunk_text(sample_text, semantic_config)
    #     print(f"成功: {semantic_result.success}")
    #     print(f"错误信息: {semantic_result.error_message}")
        
    # except Exception as e:
    #     print(f"语义分块测试失败: {e}")
