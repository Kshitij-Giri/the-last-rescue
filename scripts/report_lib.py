"""Number registry for the final report (Phase 7).

Every result number printed in report/report.docx is produced by one of the readers below. Each call reads the value from
a result file, formats it, and records {source file, locator, raw value, displayed text} in docs/report_numbers.yaml.
scripts/verify_results.py (V7) re-reads every entry from its source, re-formats it, and checks that the displayed text
appears in the rendered report. Nothing in the report is typed in by hand except design constants that are also checked
against config files through the same readers.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
MINUS = "−"


def fmt_value(v: float, fmt: str, nd: int = 3) -> str:
    """Format a number for the report. Shared by the generator and the verifier (V7)."""
    v = float(v)
    if fmt == "int":
        s = f"{int(round(v)):,}"
    elif fmt == "f":
        s = f"{v:.{nd}f}"
    elif fmt == "sf":          # signed fixed: +0.331 / -0.248
        s = ("+" if v > 0 else "") + f"{v:.{nd}f}"
    elif fmt == "pct":         # fraction -> percent
        s = f"{100 * v:.{nd}f}%"
    elif fmt == "p":           # p-value
        if v < 0.001:
            e = int(math.floor(math.log10(v)))
            m = v / 10 ** e
            if round(m, 1) >= 10:
                m, e = m / 10, e + 1
            s = f"{m:.1f} × 10^{{{e}}}"
        elif v < 0.01:
            s = f"{v:.2g}"
        elif v < 0.1:
            s = f"{v:.3g}"
            if "e" in s:
                s = f"{v:.4f}"
        else:
            s = f"{v:.2f}"
    elif fmt == "g":
        s = f"{v:g}"
    else:
        raise ValueError(fmt)
    s = s.replace("-", MINUS)
    return s


def plain(s: str) -> str:
    """Display text without inline markup (as it appears in the docx text layer)."""
    return re.sub(r"\^\{([^}]*)\}|_\{([^}]*)\}", lambda m: m.group(1) or m.group(2) or "", s).replace("**", "")


def read_source(entry: dict):
    kind, f = entry["kind"], ROOT / entry["file"]
    if kind == "json":
        v = json.loads(f.read_text())
        for k in entry["path"].split("."):
            v = v[int(k)] if isinstance(v, list) else v[k]
        return float(v)
    if kind == "yaml":
        v = yaml.safe_load(f.read_text())
        for k in entry["path"].split("."):
            v = v[k]
        return float(v)
    if kind in ("csv", "csv_agg"):
        d = pd.read_csv(f)
        for k, val in entry.get("where", {}).items():
            d = d[d[k].astype(str) == str(val)]
        if kind == "csv":
            assert len(d) == 1, f"{entry}: {len(d)} rows"
            return float(d[entry["column"]].iloc[0])
        col = d[entry["column"]]
        how = entry["agg"]
        if how == "sum":
            return float(col.sum())
        if how == "mean":
            return float(col.mean())
        if how == "count":
            return float(len(d))
        if how == "count_true":
            return float(col.astype(str).str.lower().eq("true").sum())
        if how == "max":
            return float(col.max())
        if how == "min":
            return float(col.min())
        raise ValueError(how)
    if kind == "regex":
        m = re.search(entry["pattern"], f.read_text())
        assert m, f"pattern not found: {entry['pattern']}"
        return float(m.group(1).replace(",", ""))
    if kind == "files":
        return float(len(list(ROOT.glob(entry["pattern"]))))
    raise ValueError(kind)


class Registry:
    def __init__(self):
        self.entries: dict[str, dict] = {}

    def _rec(self, entry: dict, fmt: str, nd: int, scale: float = 1.0) -> str:
        v = read_source(entry) * scale
        disp = fmt_value(v, fmt, nd)
        key = json.dumps({k: entry[k] for k in sorted(entry)}, sort_keys=True) + f"|{fmt}|{nd}|{scale}"
        e = dict(entry, value=v, fmt=fmt, nd=nd, scale=scale, display=disp)
        self.entries.setdefault(key, e)
        return disp

    # readers -------------------------------------------------------------------------------------------------
    def csv(self, file, where, column, nd=3, fmt="f", scale=1.0):
        return self._rec({"kind": "csv", "file": file, "where": where, "column": column}, fmt, nd, scale)

    def agg(self, file, where, column, how, nd=3, fmt="f", scale=1.0):
        return self._rec({"kind": "csv_agg", "file": file, "where": where, "column": column, "agg": how}, fmt, nd, scale)

    def js(self, file, path, nd=3, fmt="f", scale=1.0):
        return self._rec({"kind": "json", "file": file, "path": path}, fmt, nd, scale)

    def ym(self, file, path, nd=0, fmt="int", scale=1.0):
        return self._rec({"kind": "yaml", "file": file, "path": path}, fmt, nd, scale)

    def rx(self, file, pattern, nd=0, fmt="int"):
        return self._rec({"kind": "regex", "file": file, "pattern": pattern}, fmt, nd)

    def files(self, pattern):
        return self._rec({"kind": "files", "file": ".", "pattern": pattern}, "int", 0)

    def ci(self, file, where, m="mean", lo="ci_lo", hi="ci_hi", nd=3, fmt="f"):
        a = self.csv(file, where, m, nd, fmt)
        b = self.csv(file, where, lo, nd, "f" if fmt == "sf" else fmt)
        c = self.csv(file, where, hi, nd, "f" if fmt == "sf" else fmt)
        return f"{a} [{b}, {c}]"

    def dump(self, path: Path):
        rows = sorted(self.entries.values(), key=lambda e: (e["file"], json.dumps(e, sort_keys=True, default=str)))
        path.write_text("# Generated by scripts/build_report_content.py. Every result number shown in report/report.docx,\n"
                        "# with its source file, locator, raw value and displayed text. Checked by scripts/verify_results.py (V7).\n"
                        + yaml.safe_dump(rows, sort_keys=True, allow_unicode=True, width=200))
        return len(rows)
