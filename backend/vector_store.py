from pathlib import Path
import chromadb
from backend.config import DATA_DIR

VECTOR_DB_PATH = DATA_DIR / "vector_store"

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

    # Large textbooks can exceed Chroma's per-request batch limit.
    batch_size = client.get_max_batch_size()
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.add(ids=ids[start:end], documents=documents[start:end], metadatas=metadatas[start:end])


def delete_textbook_chunks(textbook_id):
    collection.delete(where={"textbook_id": textbook_id})


def get_textbook_chunks(textbook_id):
    return collection.get(where={"textbook_id": textbook_id}, include=["documents", "metadatas", "embeddings"])


def restore_textbook_chunks(snapshot):
    # Reuse saved embeddings: recovery never re-embeds a deleted book.
    for start in range(0, len(snapshot['ids']), client.get_max_batch_size()):
        end = start + client.get_max_batch_size()
        parameters = {name: snapshot[name][start:end] for name in ('ids', 'embeddings', 'metadatas')}
        if all(document is not None for document in snapshot['documents'][start:end]):
            parameters['documents'] = snapshot['documents'][start:end]
        collection.upsert(**parameters)


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
