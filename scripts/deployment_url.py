"""Extract Wrangler's workers.dev URL without needing another account API permission."""

import re
import sys
from pathlib import Path

log = Path(sys.argv[1]).read_text(encoding="utf-8")
urls = re.findall(r"https://fci-breeds-varieties\.[a-zA-Z0-9-]+\.workers\.dev", log)
if not urls:
    raise SystemExit("Deployment completed but workers.dev URL was not found in Wrangler output")
print(f"url={urls[-1]}")
