import fitz #PyMuPDF


def extract_text_from_pdf(file_path):
    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text() + "\n"

    page_count = document.page_count
    document.close()

    return text, page_count