"""Run trusted tiny programs; never inherit API credentials into exercises."""
import unittest
from unittest.mock import patch

from backend.code_runner import run_code_language


class CodeRunnerTests(unittest.TestCase):
    def test_exercises_do_not_inherit_api_key(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-secret-not-real'}):
            result = run_code_language('import os; print("OPENAI_API_KEY" in os.environ)', 'python')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['output'].strip(), 'False')

    def test_java_success_compile_error_and_timeout(self):
        cases = (
            ('public class Main { public static void main(String[] args) { System.out.println(42); } }', 'success'),
            ('public class Main { broken }', 'compile_error'),
            ('public class Main { public static void main(String[] args) { while(true) {} } }', 'timeout'),
        )
        for code, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(run_code_language(code, 'java')['status'], expected)

    def test_java_output_is_captured_through_bounded_shared_runner(self):
        # Avoid deliberately exhausting RAM: forbid the old capture_output path.
        from backend import code_runner
        original = code_runner.subprocess.run
        def guarded(*args, **kwargs):
            if kwargs.get('capture_output'):
                raise AssertionError('Java must not buffer unbounded exercise output in RAM')
            return original(*args, **kwargs)
        code = 'public class Main { public static void main(String[] args) { for(int i=0;i<15000;i++) System.out.print("x"); } }'
        with patch.object(code_runner.subprocess, 'run', side_effect=guarded):
            result = run_code_language(code, 'java')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(len(result['output']), 10000)

    def test_excessive_output_stops_with_a_clear_limit(self):
        result = run_code_language('print("x" * 200000); import time; time.sleep(1)', 'python')
        self.assertEqual(result['status'], 'output_limit')
        self.assertLessEqual(len(result['output']), 10000)


if __name__ == '__main__':
    unittest.main()
