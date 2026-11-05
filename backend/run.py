import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Training runs independently, but disabling the development reloader also
    # prevents accidental server restarts while a long-running job is active.
    app.run(debug=False)
