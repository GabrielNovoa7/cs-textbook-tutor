import pymupdf


def extract_pages_from_pdf(file_path):
    document = pymupdf.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start=1):
        pages.append({
            "page_number": page_number,
            "text": page.get_text()
        })

    page_count = document.page_count
    document.close()

    return pages, page_count