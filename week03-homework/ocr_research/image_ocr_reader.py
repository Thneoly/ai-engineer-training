"""Custom LlamaIndex reader that converts OCR'd images into Documents."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Sequence, Union

from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document

try:  # pragma: no cover - import guard for optional dependency
    from paddleocr import PaddleOCR
except ImportError as exc:  # pragma: no cover - import guard for optional dependency
    raise ImportError(
        "PaddleOCR is required for ImageOCRReader. Please install paddleocr and paddlepaddle."
        " Refer to https://www.paddlepaddle.org.cn/install/quick for platform specific wheels."
    ) from exc


_SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


class ImageOCRReader(BaseReader):
    """Reader that extracts text from images via PaddleOCR and returns Documents."""

    def __init__(
        self,
        lang: str = "ch",
        use_gpu: bool = False,
        ocr_version: str = "PP-OCRv4",
        **ocr_kwargs,
    ) -> None:
        """Create a new ImageOCRReader instance.

        Args:
            lang: OCR model language, e.g. 'ch', 'en'.
            use_gpu: Whether to run inference on GPU (requires proper CUDA setup).
            ocr_version: PaddleOCR version identifier (default "PP-OCRv4").
            ocr_kwargs: Extra keyword arguments forwarded to :class:`PaddleOCR`.
        """

        default_kwargs = dict(
            use_angle_cls=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            show_log=False,
        )
        default_kwargs.update(ocr_kwargs)

        self._ocr = PaddleOCR(
            lang=lang,
            use_gpu=use_gpu,
            ocr_version=ocr_version,
            **default_kwargs,
        )
        self.lang = lang
        self.ocr_version = ocr_version

    def load_data(self, file: Union[str, Path, Sequence[Union[str, Path]]]) -> List[Document]:
        """Extract text from one or more image files.

        Args:
            file: Single path, directory, or a sequence of paths.

        Returns:
            List[Document]: OCR results packaged as LlamaIndex Document objects.
        """

        image_paths = self._collect_image_paths(file)
        documents: List[Document] = []

        for path in image_paths:
            result = self._ocr.ocr(str(path), cls=True)
            text_blocks, confidences = self._parse_blocks(result)
            doc_text = self._build_plain_text(text_blocks, confidences)

            metadata = {
                "image_path": str(path.resolve()),
                "ocr_model": self.ocr_version,
                "language": self.lang,
                "num_text_blocks": len(text_blocks),
                "avg_confidence": round(sum(confidences) / len(confidences), 4)
                if confidences
                else 0.0,
            }

            documents.append(Document(text=doc_text, metadata=metadata))

        return documents

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def load_data_from_dir(self, dir_path: Union[str, Path]) -> List[Document]:
        """Process all supported images within a directory."""

        return self.load_data(Path(dir_path))

    def _collect_image_paths(
        self, target: Union[str, Path, Sequence[Union[str, Path]]]
    ) -> List[Path]:
        if isinstance(target, (str, Path)):
            targets: Iterable[Union[str, Path]] = [target]
        else:
            targets = target

        collected: List[Path] = []
        for item in targets:
            path = Path(item).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f"Image path not found: {path}")

            if path.is_dir():
                collected.extend(
                    p for p in path.rglob("*") if p.suffix.lower() in _SUPPORTED_EXTENSIONS
                )
            elif path.suffix.lower() in _SUPPORTED_EXTENSIONS:
                collected.append(path)
            else:
                raise ValueError(f"Unsupported image format: {path.suffix} ({path})")

        if not collected:
            raise ValueError("No supported image files were found for OCR processing.")

        return collected

    def _parse_blocks(self, ocr_result) -> tuple[List[str], List[float]]:
        text_blocks: List[str] = []
        confidences: List[float] = []

        for page in ocr_result:
            for line in page:
                _, (text, confidence) = line
                text_blocks.append(text.strip())
                confidences.append(float(confidence))

        return text_blocks, confidences

    def _build_plain_text(
        self, text_blocks: List[str], confidences: List[float]
    ) -> str:
        if not text_blocks:
            return ""

        formatted_lines = []
        for idx, (text, conf) in enumerate(zip(text_blocks, confidences), start=1):
            formatted_lines.append(f"[Text Block {idx}] (conf: {conf:.2f}): {text}")

        return "\n".join(formatted_lines)
