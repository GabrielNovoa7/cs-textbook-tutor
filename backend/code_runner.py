import subprocess
import tempfile
import sys
import shutil
import os
import signal
from pathlib import Path

MAX_OUTPUT_LENGTH = 10000


def run_code_language(code, language='java'):
    if language == 'java':
        try:
            return run_java_code(code)
        except FileNotFoundError:
            return {'status':'unavailable','output':'Java requires javac and java on the backend PATH.'}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        path = Path(folder)
        if language == 'python':
            (path / 'main.py').write_text(code, encoding='utf-8')
            command = [sys.executable, '-I', '-u', 'main.py']
        elif language == 'cpp':
            compiler = shutil.which('g++') or shutil.which('clang++')
            local_zig = Path(__file__).resolve().parents[1] / '.tools' / 'zig-x86_64-windows-0.15.2' / 'zig.exe'
            compiler_command = [compiler] if compiler else ([str(local_zig), 'c++'] if local_zig.exists() else None)
            if not compiler_command:
                return {'status':'unavailable','output':'C++ requires g++ or clang++ on the backend PATH. Restart the backend after installing a compiler.'}
            (path / 'main.cpp').write_text(code, encoding='utf-8')
            executable = path / ('main.exe' if sys.platform=='win32' else 'main')
            result = execute([*compiler_command,'-std=c++17','main.cpp','-o',str(executable)],path,180)
            if result['status']!='success':
                return {**result,'status':'compile_error' if result['status']=='runtime_error' else result['status']}
            command=[str(executable)]
        else:
            return {'status':'error','output':'Unsupported language.'}
        return execute(command,path,5)


def execute(command, folder, timeout):
    # Redirect to a file so a print loop cannot consume unlimited backend RAM.
    with tempfile.TemporaryFile() as output:
        try:
            process=subprocess.Popen(command,cwd=folder,stdin=subprocess.DEVNULL,
                stdout=output,stderr=output,
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if sys.platform=='win32' else 0,
                start_new_session=sys.platform!='win32')
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Stop child compilers/programs too, before cleaning the working folder.
            if sys.platform=='win32':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10)
            else:
                os.killpg(process.pid,signal.SIGKILL)
            process.wait(timeout=10)
            return {'status':'timeout','output':f'Program stopped after {timeout} seconds.'}
        except OSError:
            return {'status':'unavailable','output':'The language runtime could not be started.'}
        output.seek(0)
        text=output.read(MAX_OUTPUT_LENGTH).decode('utf-8',errors='replace')
        return {'status':'success' if process.returncode==0 else 'runtime_error','output':text}


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
