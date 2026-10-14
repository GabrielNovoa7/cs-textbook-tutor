import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from openai import RateLimitError

from backend import tutor


class TutorTests(unittest.TestCase):
    def test_paid_chat_has_no_automatic_retries_and_no_provider_storage(self):
        captured = {}
        def create(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(output_text='A grounded explanation.')
        class Client:
            def __init__(self, **options):
                captured.update(options)
                self.responses = SimpleNamespace(create=create)
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key-not-real'}), patch.object(tutor, 'OpenAI', Client):
            answer = tutor.generate_tutor_response('Explain objects', [{'page_number': 1, 'text': 'Objects hold state.'}])
        self.assertEqual(answer, 'A grounded explanation.')
        self.assertEqual(captured.get('max_retries'), 0)
        self.assertEqual(captured.get('timeout'), 90)
        self.assertIs(captured.get('store'), False)

    def test_provider_failure_is_safe_and_actionable(self):
        response = httpx.Response(429, request=httpx.Request('POST', 'https://api.openai.com/v1/responses'))
        error = RateLimitError('private provider body', response=response, body=None)
        with patch.object(tutor.client, 'get') as client:
            client.return_value.responses.create.side_effect = error
            with self.assertRaises(HTTPException) as failure:
                tutor.generate_tutor_response('Explain', [{'page_number': 1, 'text': 'Objects hold state.'}])
        self.assertEqual(failure.exception.status_code, 429)
        self.assertNotIn('private provider body', str(failure.exception.detail))


if __name__ == '__main__':
    unittest.main()
