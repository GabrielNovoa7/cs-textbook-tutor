import subprocess
import tempfile
from pathlib import Path

MAX_OUTPUT_LENGTH = 10000


def run_java_code(code: str):
    with tempfile.TemporaryDirectory() as temp_directory:
        temp_path = Path(temp_directory)

        java_file = temp_path / "Main.java"
        java_file.write_text(code, encoding="utf-8")

        try:
            compile_result = subprocess.run(
                ["javac", "Main.java"],
                cwd=temp_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "output": "Compilation timed out."}

        if compile_result.returncode != 0:
            return {
                "status": "compile_error",
                "output": compile_result.stderr[:MAX_OUTPUT_LENGTH],
            }

        try:
            run_result = subprocess.run(
                ["java", "-Xmx64m", "Main"],
                cwd=temp_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "output": "Program stopped because it ran for more than 5 seconds.",
            }

        output = run_result.stdout

        if run_result.stderr:
            output += run_result.stderr

        return {
            "status": "success" if run_result.returncode == 0 else "runtime_error",
            "output": output[:MAX_OUTPUT_LENGTH],
        }
