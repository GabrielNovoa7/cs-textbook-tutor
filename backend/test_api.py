"""API lifecycle regressions with disposable data and no paid requests."""
import io
import threading
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor

import chromadb
import pymupdf
from fastapi.testclient import TestClient

from backend import database as db, main, vector_store


class ApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        for target, name, value in ((db, 'DB_PATH', self.folder / 'test.db'),
                                    (main, 'UPLOAD_FOLDER', self.folder)):
            replacement = patch.object(target, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.collection = chromadb.EphemeralClient().create_collection(
            name='test-' + uuid4().hex, embedding_function=None)
        self.addCleanup(lambda: self.collection._client.delete_collection(self.collection.name))
        replacement = patch.object(vector_store, 'collection', self.collection)
        replacement.start()
        self.addCleanup(replacement.stop)
        db.init_db()
        self.client = TestClient(main.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)

    def pdf(self, text='Objects combine state and behavior. ' * 20):
        with pymupdf.open() as document:
            document.new_page().insert_textbox((40, 40, 550, 700), text)
            return document.tobytes()

    def upload(self, data):
        return self.client.post('/upload-textbook', files={'file': ('book.pdf', io.BytesIO(data), 'application/pdf')})

    def test_invalid_pdf_is_rejected_without_leftover_file(self):
        response = self.upload(b'not a PDF')
        self.assertEqual(response.status_code, 422)
        self.assertEqual(list(self.folder.glob('*.pdf')), [])
        self.assertEqual(db.get_textbooks(), [])

    def test_image_only_pdf_is_rejected_without_saved_book(self):
        with patch.object(main, 'add_textbook_chunks'):
            response = self.upload(self.pdf(''))
        self.assertEqual(response.status_code, 422)
        self.assertEqual(db.get_textbooks(), [])
        self.assertEqual(list(self.folder.glob('*.pdf')), [])

    def test_index_failure_rolls_back_book_chunks_and_file(self):
        def fail(textbook_id, chunks):
            self.collection.add(ids=[f'{textbook_id}-0'], embeddings=[[1., 0.]],
                                metadatas=[{'textbook_id': textbook_id}])
            raise RuntimeError('private provider detail')
        with patch.object(main, 'add_textbook_chunks', side_effect=fail):
            response = self.upload(self.pdf())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private provider detail', response.text)
        self.assertEqual(db.get_textbooks(), [])
        self.assertEqual(self.collection.count(), 0)
        self.assertEqual(list(self.folder.glob('*.pdf')), [])
        with closing(db.get_connection()) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM chunks').fetchone()[0], 0)

    def test_upload_duplicate_and_delete_keep_stores_consistent(self):
        def index(textbook_id, chunks):
            self.collection.add(ids=[f'{textbook_id}-{c["chunk_id"]}' for c in chunks],
                                embeddings=[[1., 0.] for _ in chunks],
                                metadatas=[{'textbook_id': textbook_id} for _ in chunks])
        data = self.pdf()
        with patch.object(main, 'add_textbook_chunks', side_effect=index):
            first = self.upload(data)
            duplicate = self.upload(data)
        self.assertEqual(first.status_code, 200)
        book_id = first.json()['textbook_id']
        self.assertTrue(duplicate.json()['already_exists'])
        self.assertEqual(len(list(self.folder.glob('*.pdf'))), 1)
        self.assertGreater(self.collection.count(), 0)
        self.collection.add(ids=['other-book'], embeddings=[[0., 1.]], metadatas=[{'textbook_id': 999}])
        self.assertEqual(self.client.delete(f'/textbooks/{book_id}').status_code, 200)
        self.assertEqual(self.collection.get()['ids'], ['other-book'])
        self.assertEqual(db.get_textbooks(), [])
        self.assertEqual(list(self.folder.glob('*.pdf')), [])

    def test_blank_questions_and_missing_books_do_not_reach_ai(self):
        with patch.object(main, 'search_textbook', side_effect=AssertionError('retrieval should not run')):
            self.assertEqual(self.client.post('/textbooks/999/ask', json={'question': '   '}).status_code, 422)
            self.assertEqual(self.client.post('/textbooks/999/ask', json={'question': 'Explain objects'}).status_code, 404)
        self.assertEqual(self.client.post('/textbooks/999/chats', json={'title': 'Study'}).status_code, 404)

    def test_localhost_and_ipv4_frontends_are_allowed(self):
        for origin in ('http://localhost:5173', 'http://127.0.0.1:5173'):
            response = self.client.options('/textbooks', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'GET'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers.get('access-control-allow-origin'), origin)

    def test_saved_learning_path_exposes_missing_section_warning(self):
        book_id = db.save_textbook('book.pdf', 'book.pdf', 'warning-hash', 10, 100, [])
        db.save_learning_path(book_id, [{'number': '1', 'title': 'Basics', 'sections': [
            {'number': '1.1', 'title': 'First', 'book_page': 1},
            {'number': '1.3', 'title': 'Third', 'book_page': 5},
        ]}])
        response = self.client.get(f'/textbooks/{book_id}/learning-path')
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['section'] for item in response.json().get('warnings', [])], ['1.2'])

    def test_duplicate_does_not_report_success_for_unfinished_index(self):
        started, finish = threading.Event(), threading.Event()
        def fail_later(textbook_id, chunks):
            started.set()
            finish.wait(timeout=5)
            raise RuntimeError('index failed')
        data = self.pdf()
        with patch.object(main, 'add_textbook_chunks', side_effect=fail_later), ThreadPoolExecutor() as pool:
            first = pool.submit(self.upload, data)
            try:
                self.assertTrue(started.wait(timeout=5))
                duplicate = self.upload(data)
                self.assertEqual(duplicate.status_code, 409)
                self.assertEqual(db.get_textbooks(), [])
            finally:
                finish.set()
            self.assertEqual(first.result().status_code, 503)
        self.assertEqual(db.get_textbooks(), [])

    def test_failed_pdf_delete_preserves_book_and_search_vectors(self):
        book_id = db.save_textbook('book.pdf', 'book.pdf', 'delete-hash', 1, 100, [])
        (self.folder / 'book.pdf').write_bytes(self.pdf())
        self.collection.add(ids=[f'{book_id}-0'], embeddings=[[1., 0.]], metadatas=[{'textbook_id': book_id}])
        with patch.object(Path, 'unlink', side_effect=PermissionError('PDF is open')):
            response = self.client.delete(f'/textbooks/{book_id}')
        self.assertEqual(response.status_code, 503)
        self.assertIsNotNone(db.get_textbook(book_id))
        self.assertEqual(self.collection.count(), 1)
        self.assertTrue((self.folder / 'book.pdf').exists())

    def test_upload_limit_cleans_up_partial_file(self):
        with patch.object(main, 'MAX_UPLOAD_BYTES', 8):
            response = self.upload(b'123456789')
        self.assertEqual(response.status_code, 413)
        self.assertEqual(list(self.folder.glob('*.pdf')), [])
        self.assertEqual(db.get_textbooks(), [])

    def test_partial_vector_delete_failure_restores_saved_embeddings(self):
        book_id = db.save_textbook('book.pdf', 'book.pdf', 'restore-hash', 1, 100, [])
        (self.folder / 'book.pdf').write_bytes(self.pdf())
        self.collection.add(ids=[f'{book_id}-0'], embeddings=[[1., 0.]],
                            documents=['Objects hold state.'], metadatas=[{'textbook_id': book_id}])
        def fail_after_delete(textbook_id):
            vector_store.delete_textbook_chunks(textbook_id)
            raise RuntimeError('private vector error')
        with patch.object(main, 'delete_textbook_chunks', side_effect=fail_after_delete):
            response = self.client.delete(f'/textbooks/{book_id}')
        self.assertEqual(response.status_code, 503)
        self.assertIsNotNone(db.get_textbook(book_id))
        restored = self.collection.get(include=['embeddings', 'documents'])
        self.assertEqual(restored['documents'], ['Objects hold state.'])
        self.assertEqual(restored['embeddings'].tolist(), [[1., 0.]])
        self.assertTrue((self.folder / 'book.pdf').exists())

    def test_large_index_is_split_without_losing_chunks(self):
        stored = []
        class LimitedIndex:
            def add(self, ids, documents, metadatas):
                if len(ids) > 2:
                    raise ValueError('batch too large')
                stored.extend(zip(ids, documents, metadatas))
        chunks = [{'chunk_id': i, 'text': f'Paragraph {i}', 'page_number': i + 1} for i in range(5)]
        with patch.object(vector_store, 'collection', LimitedIndex()), \
                patch.object(vector_store.client, 'get_max_batch_size', return_value=2):
            vector_store.add_textbook_chunks(7, chunks)
        self.assertEqual([row[0] for row in stored], ['7-0', '7-1', '7-2', '7-3', '7-4'])
        self.assertEqual([row[1] for row in stored], ['Paragraph 0', 'Paragraph 1', 'Paragraph 2', 'Paragraph 3', 'Paragraph 4'])

    def test_failed_backup_restore_keeps_recoverable_pdf(self):
        book_id = db.save_textbook('book.pdf', 'book.pdf', 'backup-hash', 1, 100, [])
        pdf = self.pdf()
        (self.folder / 'book.pdf').write_bytes(pdf)
        class FailedCommit:
            def __init__(self):
                self.connection = db.get_connection()
            def __enter__(self):
                return self.connection
            def execute(self, *arguments):
                return self.connection.execute(*arguments)
            def __exit__(self, *error):
                self.connection.rollback()
                raise sqlite3.OperationalError('commit failed')
            def close(self):
                self.connection.close()
        with patch.object(main, 'get_connection', side_effect=FailedCommit), \
                patch.object(Path, 'replace', side_effect=PermissionError('restore failed')):
            response = self.client.delete(f'/textbooks/{book_id}')
        self.assertEqual(response.status_code, 503)
        backups = list(self.folder.glob('*.deleting'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), pdf)
        self.assertIsNotNone(db.get_textbook(book_id))


if __name__ == '__main__':
    unittest.main()
