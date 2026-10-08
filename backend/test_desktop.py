"""Desktop integration checks; no API calls or user data changes."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path


class DesktopIntegration(unittest.TestCase):
    def test_fresh_profile_authenticated_backend_and_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {**os.environ, 'CSTUTOR_DATA_DIR': directory,
                   'CSTUTOR_DESKTOP_MODE': '1', 'CSTUTOR_DESKTOP_TOKEN': 'test-desktop-token',
                   'OPENAI_API_KEY': '', 'PYTHONUNBUFFERED': '1'}
            executable = os.getenv('CSTUTOR_TEST_EXE', sys.executable)
            if os.getenv('CSTUTOR_TEST_EXE'):
                env['CSTUTOR_PYTHON_RUNTIME'] = str(Path(executable).parent / 'python-runtime/python.exe')
            command = [executable] if os.getenv('CSTUTOR_TEST_EXE') else [executable, '-m', 'backend.desktop_entry']
            process = subprocess.Popen(command, env=env, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                line = process.stdout.readline()
                self.assertTrue(line.startswith('DESKTOP_READY:'), 'Backend did not announce readiness')
                base = 'http://127.0.0.1:' + str(json.loads(line.split(':', 1)[1])['port'])
                def request(path, data=None, headers=None, method=None):
                    return urllib.request.urlopen(urllib.request.Request(base + path, data=data,
                        headers=headers or {'X-Desktop-Token': 'test-desktop-token'}, method=method), timeout=10)
                for _ in range(100):
                    try:
                        with request('/health') as response:
                            self.assertEqual(json.load(response)['status'], 'ready')
                        break
                    except urllib.error.URLError:
                        time.sleep(.1)
                else:
                    self.fail('Backend readiness timeout')
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request('/textbooks', headers={'X-Desktop-Token': 'wrong'})
                self.assertEqual(error.exception.code, 401)
                with request('/textbooks') as response:
                    self.assertEqual(json.load(response), [])
                with request('/run-code', json.dumps({'code': 'print(6 * 7)', 'language': 'python'}).encode(),
                     {'X-Desktop-Token': 'test-desktop-token', 'Content-Type': 'application/json'}) as response:
                    result = json.load(response)
                    self.assertEqual(result['status'], 'success')
                    self.assertEqual(result['output'].strip(), '42')
                with request('/health', headers={'Origin': 'null', 'Access-Control-Request-Method': 'GET',
                     'Access-Control-Request-Headers': 'x-desktop-token'}, method='OPTIONS') as response:
                    self.assertEqual(response.headers['Access-Control-Allow-Origin'], 'null')
                with request('/desktop/api-key', json.dumps({'key': 'test-key-not-real'}).encode(),
                     {'X-Desktop-Token': 'test-desktop-token', 'Content-Type': 'application/json'}) as response:
                    self.assertTrue(json.load(response)['saved'])
                self.assertNotIn('test-key-not-real', (Path(directory) / 'tutor.db').read_bytes().decode('latin1'))
                # A lost parent pipe also shuts down the backend.
                process.stdin.close()
                self.assertEqual(process.wait(timeout=20), 0)
            finally:
                if process.poll() is None:
                    process.kill(); process.wait()
                process.stdin.close(); process.stdout.close(); process.stderr.close()


if __name__ == '__main__':
    unittest.main()
