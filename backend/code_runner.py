import subprocess
import tempfile
import sys
import shutil
import os
import signal
import time
from pathlib import Path

from backend.config import CPP_COMPILER, PYTHON_RUNTIME

MAX_OUTPUT_LENGTH = 10000
MAX_CAPTURE_BYTES = 100000


def stop_process(process):
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=10)


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
            command = [PYTHON_RUNTIME or sys.executable, '-I', '-u', 'main.py']
        elif language == 'cpp':
            compiler = shutil.which('g++') or shutil.which('clang++')
            local_zig = Path(CPP_COMPILER) if CPP_COMPILER else Path(__file__).resolve().parents[1] / '.tools' / 'zig-x86_64-windows-0.15.2' / 'zig.exe'
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
            # Exercise programs need runtimes and temp paths, not backend credentials.
            allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT',
                       'TEMP', 'TMP', 'HOME', 'USERPROFILE', 'LOCALAPPDATA',
                       'APPDATA', 'JAVA_HOME', 'LANG', 'LC_ALL'}
            environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
            process=subprocess.Popen(command,cwd=folder,stdin=subprocess.DEVNULL,env=environment,
                stdout=output,stderr=output,
                creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if sys.platform=='win32' else 0,
                start_new_session=sys.platform!='win32')
            deadline = time.monotonic() + timeout
            exceeded_output = False
            while process.poll() is None:
                if os.fstat(output.fileno()).st_size > MAX_CAPTURE_BYTES:
                    exceeded_output = True
                    stop_process(process)
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    process.wait(timeout=min(.05, remaining))
                except subprocess.TimeoutExpired:
                    pass
        except subprocess.TimeoutExpired:
            # Stop child compilers/programs too, before cleaning the working folder.
            stop_process(process)
            return {'status':'timeout','output':f'Program stopped after {timeout} seconds.'}
        except OSError:
            return {'status':'unavailable','output':'The language runtime could not be started.'}
        output.seek(0)
        text=output.read(MAX_OUTPUT_LENGTH).decode('utf-8',errors='replace')
        if exceeded_output or os.fstat(output.fileno()).st_size > MAX_CAPTURE_BYTES:
            return {'status': 'output_limit', 'output': text[:MAX_OUTPUT_LENGTH - 100] + '\nProgram stopped: output limit exceeded.'}
        return {'status':'success' if process.returncode==0 else 'runtime_error','output':text}


def run_java_code(code: str):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_directory:
        temp_path = Path(temp_directory)

        java_file = temp_path / "Main.java"
        java_file.write_text(code, encoding="utf-8")

        compiled = execute(["javac", "Main.java"], temp_path, 5)
        if compiled['status'] != 'success':
            return {**compiled, 'status': 'compile_error' if compiled['status'] == 'runtime_error' else compiled['status']}
        return execute(["java", "-Xmx64m", "Main"], temp_path, 5)
