"""PDF previews cached by file version without altering uploaded books."""
from functools import lru_cache
import pymupdf


@lru_cache(maxsize=64)
def render_cover(path: str, modified_ns: int, file_size: int):
    with pymupdf.open(path) as document:
        if not document.page_count:
            raise ValueError('The PDF has no pages.')
        page = document[0]
        scale = min(320 / page.rect.width, 480 / page.rect.height)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes('png')
