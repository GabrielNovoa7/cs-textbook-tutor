from pathlib import Path
import chromadb

VECTOR_DB_PATH = Path(__file__).resolve().parent / "vector_store"

client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))

collection = client.get_or_create_collection(name="textbook_chunks")


def add_textbook_chunks(textbook_id, chunks):
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        ids.append(f"{textbook_id}-{chunk['chunk_id']}")

        documents.append(chunk["text"])

        metadatas.append(
            {
                "textbook_id": textbook_id,
                "chunk_id": chunk["chunk_id"],
                "page_number": chunk["page_number"],
            }
        )

    collection.add(ids=ids, documents=documents, metadatas=metadatas)


def search_textbook(textbook_id, query, results=5):
    search_results = collection.query(
        query_texts=[query],
        n_results=results,
        where={"textbook_id": textbook_id},
        include=["documents", "metadatas", "distances"],
    )

    matches = []

    if not search_results["documents"]:
        return matches

    for index, text in enumerate(search_results["documents"][0]):
        metadata = search_results["metadatas"][0][index]
        distance = search_results["distances"][0][index]

        matches.append(
            {
                "text": text,
                "page_number": metadata["page_number"],
                "chunk_id": metadata["chunk_id"],
                "distance": distance,
            }
        )

    return matches
