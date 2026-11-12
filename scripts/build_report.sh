#!/usr/bin/env bash
# Build report/report.docx and report/report.pdf from the verified result files (two passes for the static contents page).
set -euo pipefail
cd "$(dirname "$0")/.."
SOFFICE="python /root/.claude/skills/synced/2ee58891-1c34-4b0f-a3ca-b4de3e8eb6f7_b68d40ea-1d1b-495b-92b1-7f9781de75ce/docx/scripts/office/soffice.py"
command -v soffice >/dev/null && SOFFICE="soffice"
python scripts/make_report_diagrams.py
python scripts/build_report_content.py
rm -f report/toc_pages.json
node scripts/render_report.js
(cd report && zip -d report.docx '*/' >/dev/null 2>&1 || true; $SOFFICE --headless --convert-to pdf report.docx >/dev/null 2>&1)
python scripts/toc_pages.py report/report.pdf report/toc_pages.json
node scripts/render_report.js --toc report/toc_pages.json
(cd report && zip -d report.docx '*/' >/dev/null 2>&1 || true; $SOFFICE --headless --convert-to pdf report.docx >/dev/null 2>&1)
python scripts/toc_pages.py report/report.pdf report/toc_pages_check.json
cmp -s report/toc_pages.json report/toc_pages_check.json && echo "contents page numbers stable" || echo "WARNING: contents page numbers moved"
rm -f report/toc_pages_check.json
