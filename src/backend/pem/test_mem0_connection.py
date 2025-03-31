# Remove unused imports
# import sys
# from pathlib import Path

from src.common.logger import logger
from src.common.mem0_client import Mem0Client

# Add root COS path to system path
# root_path = Path(__file__).resolve().parents[2]  # cos/
# sys.path.insert(0, str(root_path / "src"))

# Import after path adjustment


def test_mem0_from_pem() -> None:
    mem = Mem0Client()
    key = "pem-log-001"
    data = {"step": "connected from PEM", "status": "✅"}
    logger.info(f"Setting memory for key '{key}': {data}")
    mem.set(key, data)
    retrieved_data = mem.get(key)
    logger.info(f"Retrieved memory for key '{key}': {retrieved_data}")


if __name__ == "__main__":
    test_mem0_from_pem()
