def chunk_pages(pages, chunk_size=1500, overlap=250):
    chunks = []

    chunk_id = 0

    for page in pages:
        text = page["text"].strip()

        if not text:
            continue

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "page_number": page["page_number"],
                        "text": chunk_text,
                    }
                )

                chunk_id += 1

            if end == len(text):
                break

            start = end - overlap

    return chunks
