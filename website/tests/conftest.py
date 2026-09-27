import sys
from pathlib import Path

WEBSITE = Path(__file__).resolve().parents[1]
REPO = WEBSITE.parent
sys.path.insert(0, str(WEBSITE))
