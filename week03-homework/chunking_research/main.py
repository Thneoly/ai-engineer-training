import os
from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader, Document
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
    SentenceWindowNodeParser
)
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
import time
from typing import List

# 加载环境变量
load_dotenv()

def setup_llama_index():
    """设置 LlamaIndex 使用 Qwen 模型"""
    Settings.llm = OpenAILike(
        model="qwen-plus",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        is_chat_model=True,
        timeout=60
    )
    
    Settings.embed_model = DashScopeEmbedding(
        model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
        embed_batch_size=6,
        embed_input_length=8192
    )
    print(" LlamaIndex 配置完成")


def load_documents(doc_dir: str = "./documents"):
    """加载文档"""
    reader = SimpleDirectoryReader(doc_dir)
    documents = reader.load_data()
    print(f" 加载了 {len(documents)} 个文档")
    for i, doc in enumerate(documents):
        print(f"  文档 {i+1}: {len(doc.text)} 字符")
    return documents


def evaluate_splitter(splitter, documents: List[Document], question: str, ground_truth: str, splitter_name: str):
    """评估切片器性能"""
    print(f"\n{'='*60}")
    print(f"测试切片器: {splitter_name}")
    print(f"{'='*60}")
    
    # 获取节点
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"切片数量: {len(nodes)}")
    
    # 显示前3个节点的信息
    print("\n节点样例:")
    for i, node in enumerate(nodes[:3]):
        text_preview = node.get_content()[:100].replace('\n', ' ')
        print(f"  节点 {i+1}: {text_preview}...")
    
    # 构建索引
    print("\n构建向量索引...")
    start_time = time.time()
    index = VectorStoreIndex(nodes)
    index_time = time.time() - start_time
    print(f"索引构建耗时: {index_time:.2f} 秒")
    
    # 创建查询引擎
    if "Window" in splitter_name:
        query_engine = index.as_query_engine(
            similarity_top_k=5,
            node_postprocessors=[MetadataReplacementPostProcessor(target_metadata_key="window")]
        )
    else:
        query_engine = index.as_query_engine(similarity_top_k=5)
    
    # 执行查询
    print(f"\n问题: {question}")
    print("查询中...")
    start_time = time.time()
    response = query_engine.query(question)
    query_time = time.time() - start_time
    
    print(f"\n回答: {response}")
    print(f"\n查询耗时: {query_time:.2f} 秒")
    print(f"\n参考答案: {ground_truth}")
    
    # 显示检索到的上下文
    if hasattr(response, 'source_nodes') and response.source_nodes:
        print(f"\n检索到 {len(response.source_nodes)} 个相关节点:")
        for i, node in enumerate(response.source_nodes[:3]):
            print(f"\n  节点 {i+1} (相似度: {node.score:.4f}):")
            text_preview = node.get_content()[:200].replace('\n', ' ')
            print(f"  {text_preview}...")
    
    return {
        'splitter_name': splitter_name,
        'num_nodes': len(nodes),
        'index_time': index_time,
        'query_time': query_time,
        'response': str(response)
    }


def main():
    """作业一主函数：探索不同切片策略"""
    print("="*60)
    print("作业一: LlamaIndex 句子切片检索及参数影响分析")
    print("="*60)
    
    # 1. 设置环境
    setup_llama_index()
    
    # 2. 加载文档
    documents = load_documents("./documents")
    
    # 3. 定义测试问题
    question = "数字经济在'十四五'期间有哪些重要发展成就？"
    ground_truth = "数字经济核心产业增加值比'十三五'末增长73.8%，占GDP比重达到10.4%；建成全球规模最大的信息通信网络，算力总规模全球第二"
    
    results = []
    
    # 策略1: 句子切片 - 基础配置
    print("\n\n实验 1: 句子切片 (基础配置 512/50)")
    result1 = evaluate_splitter(
        SentenceSplitter(chunk_size=512, chunk_overlap=50),
        documents, question, ground_truth, "Sentence (512/50)"
    )
    results.append(result1)
    
    # 策略2: 句子切片 - 较大chunk_size
    print("\n\n实验 2: 句子切片 (较大chunk_size 1024/100)")
    result2 = evaluate_splitter(
        SentenceSplitter(chunk_size=1024, chunk_overlap=100),
        documents, question, ground_truth, "Sentence (1024/100)"
    )
    results.append(result2)
    
    # 策略3: 句子切片 - 较小chunk_size
    print("\n\n实验 3: 句子切片 (较小chunk_size 256/25)")
    result3 = evaluate_splitter(
        SentenceSplitter(chunk_size=256, chunk_overlap=25),
        documents, question, ground_truth, "Sentence (256/25)"
    )
    results.append(result3)
    
    # 策略4: 句子切片 - 无重叠
    print("\n\n实验 4: 句子切片 (无重叠 512/0)")
    result4 = evaluate_splitter(
        SentenceSplitter(chunk_size=512, chunk_overlap=0),
        documents, question, ground_truth, "Sentence (512/0)"
    )
    results.append(result4)
    
    # 策略5: Token切片
    print("\n\n实验 5: Token 切片 (256/32)")
    result5 = evaluate_splitter(
        TokenTextSplitter(chunk_size=256, chunk_overlap=32, separator=" "),
        documents, question, ground_truth, "Token (256/32)"
    )
    results.append(result5)
    
    # 策略6: 句子窗口切片
    print("\n\n实验 6: 句子窗口切片 (window_size=3)")
    result6 = evaluate_splitter(
        SentenceWindowNodeParser.from_defaults(
            window_size=3,
            window_metadata_key="window",
            original_text_metadata_key="original_text"
        ),
        documents, question, ground_truth, "Sentence Window (3)"
    )
    results.append(result6)
    
    # 5. 输出汇总结果
    print("\n\n" + "="*60)
    print("实验结果汇总")
    print("="*60)
    print(f"{'切片策略':<25} {'节点数':<10} {'索引时间(s)':<15} {'查询时间(s)':<15}")
    print("-"*60)
    for result in results:
        print(f"{result['splitter_name']:<25} {result['num_nodes']:<10} {result['index_time']:<15.2f} {result['query_time']:<15.2f}")
    
    print("\n 实验完成！请根据上述结果补充 report.md")


if __name__ == "__main__":
    main()
