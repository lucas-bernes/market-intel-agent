"""Gera um HTML único (dados embutidos) do dashboard, pra abrir sem servidor.

Uso:
    cd frontend && npm run build && cd ..
    python scripts/export_static.py

Saída: export/market-intel-snapshot.html
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from market_intel.api import list_history, list_models, list_providers

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist"
OUT = ROOT / "export" / "market-intel-snapshot.html"

# "</" dentro de um <script> fecharia a tag antes da hora.
CLOSE_TAG_SAFE = ("</", "<\\/")


def main() -> None:
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": [m.model_dump(mode="json") for m in list_models()],
        "providers": [p.model_dump(mode="json") for p in list_providers()],
        "history": [h.model_dump(mode="json") for h in list_history()],
    }
    snapshot_js = json.dumps(snapshot, ensure_ascii=False).replace(*CLOSE_TAG_SAFE)

    html = (DIST / "index.html").read_text(encoding="utf-8")

    def read_asset(path: str) -> str:
        return (DIST / path.lstrip("/")).read_text(encoding="utf-8").replace("</script", "<\\/script")

    # CSS e JS do build viram inline; o favicon externo sai.
    html = re.sub(r'<link rel="icon"[^>]*>', "", html)
    html = re.sub(
        r'<link rel="stylesheet"[^>]*href="([^"]+)"[^>]*>',
        lambda m: f"<style>{read_asset(m.group(1))}</style>",
        html,
    )
    script_re = r'<script type="module"[^>]*src="([^"]+)"[^>]*></script>'
    js = read_asset(re.search(script_re, html).group(1))
    html = re.sub(script_re, "", html)
    html = html.replace(
        "</body>",
        f'<script>window.__SNAPSHOT__ = {snapshot_js};</script>\n<script type="module">{js}</script>\n</body>',
    )

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"OK: {OUT} ({OUT.stat().st_size // 1024} KB, {len(snapshot['models'])} modelos, {len(snapshot['providers'])} provedores)")


if __name__ == "__main__":
    main()
