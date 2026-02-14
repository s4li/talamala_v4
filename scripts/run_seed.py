"""Wrapper to run seed.py with UTF-8 encoding on Windows."""
import sys
import io
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Forward args
sys.argv = ["seed.py"] + sys.argv[1:]

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

exec(open("scripts/seed.py", encoding="utf-8").read())
