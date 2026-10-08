import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('CSTUTOR_DATA_DIR', BACKEND_DIR)).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DESKTOP_TOKEN = os.environ.get('CSTUTOR_DESKTOP_TOKEN', '')
CPP_COMPILER = os.environ.get('CSTUTOR_CPP_COMPILER', '')
PYTHON_RUNTIME = os.environ.get('CSTUTOR_PYTHON_RUNTIME', '')
