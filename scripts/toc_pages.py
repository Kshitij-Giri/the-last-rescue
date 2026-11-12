"""Find the PDF page of every level-1/2 heading of report/content.json (for the static table of contents).
Usage: python scripts/toc_pages.py report/report.pdf report/toc_pages.json"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pdf, out = sys.argv[1], sys.argv[2]
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
pages = [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf, "-"], capture_output=True, text=True).stdout
         for i in range(1, n + 1)]
norm = lambda s: re.sub(r"\s+", " ", s).strip()
lines = [[norm(l) for l in p.splitlines() if l.strip()] for p in pages]
plain = lambda t: re.sub(r"[_^]\{([^}]*)\}", r"\1", t).replace("**", "").replace("*", "")
blocks = json.loads((ROOT / "report" / "content.json").read_text())["blocks"]
start = next(i for i, p in enumerate(lines) if p and p[0].startswith("Contents") or any(l == "Contents" for l in p)) + 1
# skip TOC pages: first page after "Contents" whose lines do not end with a page number leader
while start < n and sum(bool(re.search(r"\.{3,}\s*\d+$", l)) for l in lines[start]) > 3:
    start += 1
res, cur = {}, start
for b in blocks:
    if b["t"] not in ("h1", "h2") or b["text"] == "Summary":
        continue
    key = norm(plain(b["text"]))
    probe = key[:45]
    for i in range(cur, n):
        if any(l.startswith(probe) or probe.startswith(l[:45]) and len(l) > 20 and key.startswith(l) for l in lines[i]):
            res[key] = i + 1
            cur = i
            break
    else:
        print("NOT FOUND:", key)
Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False))
print(f"{len(res)} headings located; pdf pages {n}")
