"""Entry point for the OCR research assignment."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.dashscope import (
    DashScopeEmbedding,
    DashScopeTextEmbeddingModels,
)
from llama_index.llms.openai_like import OpenAILike

from .image_ocr_reader import ImageOCRReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from images via PaddleOCR and optionally query with LlamaIndex.",
    )
    parser.add_argument(
        "--images",
        nargs="*",
        default=None,
        help="One or more image paths or directories. Defaults to ocr_research/sample_images.",
    )
    parser.add_argument(
        "--lang",
        default="ch",
        help="Language for PaddleOCR model (e.g., 'ch', 'en').",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        help="Enable GPU acceleration if PaddleOCR was installed with CUDA support.",
    )
    parser.add_argument(
        "--question",
        default="图片中提到了什么关键信息？",
        help="Question used for LlamaIndex demo query.",
    )
    parser.add_argument(
        "--skip-query",
        action="store_true",
        help="Only perform OCR without building an index or running a query.",
    )
    return parser.parse_args()


def configure_llama_index() -> bool:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        logging.warning("DASHSCOPE_API_KEY is not set. Skipping LlamaIndex query demo.")
        return False

    Settings.llm = OpenAILike(
        model="qwen-plus",
        api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=api_key,
        is_chat_model=True,
        timeout=120,
    )
    Settings.embed_model = DashScopeEmbedding(
        model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V3,
        embed_batch_size=6,
        embed_input_length=8192,
    )
    return True


def discover_default_images() -> List[str]:
    default_dir = Path(__file__).resolve().parent / "sample_images"
    if not default_dir.exists():
        return []
    return [str(p) for p in default_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]


def main() -> None:
    load_dotenv()
    args = parse_args()

    image_inputs = args.images if args.images else discover_default_images()
    if not image_inputs:
        raise SystemExit(
            "No images were provided. Use --images to specify files or place samples under"
            " ocr_research/sample_images."
        )

    reader = ImageOCRReader(lang=args.lang, use_gpu=args.use_gpu)
    documents = reader.load_data(image_inputs)

    print("\n================ OCR SUMMARY ================")
    for doc in documents:
        meta = doc.metadata
        print(
            f"Image: {meta['image_path']} | blocks: {meta['num_text_blocks']} | "
            f"avg_conf: {meta['avg_confidence']:.2f}"
        )

    if args.skip_query:
        return

    if not configure_llama_index():
        return

    index = VectorStoreIndex.from_documents(documents)
    query_engine = index.as_query_engine()
    response = query_engine.query(args.question)

    print("\n================ QUERY RESULT ================")
    print(response)


if __name__ == "__main__":
    main()

# source .venv/bin/activate && python -m ocr_research.main --images ocr_research/sample_images --skip-query
# None of PyTorch, TensorFlow >= 2.0, or Flax have been found. Models won't be available and only tokenizers, configuration and file/data utilities can be used.
# /home/cc/Desktop/code/AIPro/ai-engineer-training/week03-homework/.venv/lib/python3.11/site-packages/paddle/utils/cpp_extension/extension_utils.py:718: UserWarning: No ccache found. Please be aware that recompiling all source files may be required. You can download and install ccache from: https://github.com/ccache/ccache/blob/master/doc/INSTALL.md
#   warnings.warn(warning_message)
# download https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar to /home/cc/.paddleocr/whl/det/ch/ch_PP-OCRv4_det_infer/ch_PP-OCRv4_det_infer.tar
# 100%|███████████████████████████████████████████████████████████████| 4780/4780 [00:01<00:00, 4686.31it/s]
# download https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar to /home/cc/.paddleocr/whl/rec/ch/ch_PP-OCRv4_rec_infer/ch_PP-OCRv4_rec_infer.tar
# 100%|█████████████████████████████████████████████████████████████| 10720/10720 [00:02<00:00, 5188.75it/s]
# download https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar to /home/cc/.paddleocr/whl/cls/ch_ppocr_mobile_v2.0_cls_infer/ch_ppocr_mobile_v2.0_cls_infer.tar
# 100%|███████████████████████████████████████████████████████████████| 2138/2138 [00:00<00:00, 3811.20it/s]
# [2025/12/05 19:47:10] ppocr WARNING: Since the angle classifier is not initialized, it will not be used during the forward process
# [2025/12/05 19:47:10] ppocr WARNING: Since the angle classifier is not initialized, it will not be used during the forward process
# [2025/12/05 19:47:10] ppocr WARNING: Since the angle classifier is not initialized, it will not be used during the forward process

# ================ OCR SUMMARY ================
# Image: /home/cc/Desktop/code/AIPro/ai-engineer-training/week03-homework/ocr_research/sample_images/ui_screenshot.png | blocks: 3 | avg_conf: 0.74
# Image: /home/cc/Desktop/code/AIPro/ai-engineer-training/week03-homework/ocr_research/sample_images/street_sign.png | blocks: 3 | avg_conf: 0.82
# Image: /home/cc/Desktop/code/AIPro/ai-engineer-training/week03-homework/ocr_research/sample_images/scan_doc.png | blocks: 2 | avg_conf: 0.73
# (week03-homework) (demo) cc@cc-pc:~/Desktop/code/AIPro/ai-engineer-training/week03-homework$ 