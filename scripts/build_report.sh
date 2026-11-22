#!/usr/bin/env bash
# Build report/report.docx and report/report.pdf from the verified result files (two passes for the static contents page).
set -euo pipefail
cd "$(dirname "$0")/.."
# LibreOffice converts the docx to PDF. On macOS the binary is inside the app bundle.
if command -v soffice >/dev/null; then
  SOFFICE="soffice"
elif [ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]; then
  SOFFICE="/Applications/LibreOffice.app/Contents/MacOS/soffice"
else
  SOFFICE=""
fi
PY="${PYTHON:-python}"
$PY scripts/make_report_diagrams.py
$PY scripts/build_report_content.py
rm -f report/toc_pages.json
node scripts/render_report.js
if [ -z "$SOFFICE" ]; then
  echo "LibreOffice (soffice) not found: built report/report.docx only. Export it to report/report.pdf to finish." >&2
  exit 0
fi
(cd report && zip -d report.docx '*/' >/dev/null 2>&1 || true; $SOFFICE --headless --convert-to pdf report.docx >/dev/null 2>&1)
$PY scripts/toc_pages.py report/report.pdf report/toc_pages.json
node scripts/render_report.js --toc report/toc_pages.json
(cd report && zip -d report.docx '*/' >/dev/null 2>&1 || true; $SOFFICE --headless --convert-to pdf report.docx >/dev/null 2>&1)
$PY scripts/toc_pages.py report/report.pdf report/toc_pages_check.json
cmp -s report/toc_pages.json report/toc_pages_check.json && echo "contents page numbers stable" || echo "WARNING: contents page numbers moved"
rm -f report/toc_pages_check.json
