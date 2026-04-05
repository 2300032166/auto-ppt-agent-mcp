import logging
import os

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("PPT-Agent")

def ensure_directory(path):
    """Ensures that the directory for the given path exists."""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory: {path}")

def format_bullet_points(content):
    """Formats raw text into a list of bullet points."""
    if isinstance(content, list):
        return content
    # Simple split by newline or bullet character
    lines = content.split('\n')
    bullets = [line.strip().lstrip('-').lstrip('*').strip() for line in lines if line.strip()]
    return bullets[:5] # Max 5 bullets per slide
