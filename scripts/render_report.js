// Render report/content.json (from scripts/build_report_content.py) to report/report.docx.
// Usage: node scripts/render_report.js [--toc report/toc_pages.json]
// The table of contents is static: page numbers come from a first rendering (scripts/build_report.sh does both passes).
"use strict";
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  AlignmentType, HeadingLevel, LevelFormat, PageBreak, Footer, Header, PageNumber, TabStopType, TabStopPosition,
  VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const content = JSON.parse(fs.readFileSync(path.join(ROOT, "report", "content.json"), "utf8")).blocks;
const tocArg = process.argv.indexOf("--toc");
const tocPages = tocArg > 0 && fs.existsSync(process.argv[tocArg + 1]) ? JSON.parse(fs.readFileSync(process.argv[tocArg + 1], "utf8")) : {};

const FONT = "Arial";
const MONO = "Courier New";
const BODY = 21;            // half-points (10.5 pt)
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1300;
const CW = PAGE_W - 2 * MARGIN;   // content width (DXA)
const INK = "1F1F1F", MUTED = "555555", ACCENT = "1F4E79", RULE = "BFBFBF";

// ---------- inline markup: **bold**, *italic*, `code`, _{sub}, ^{sup} ----------------------------------------------
function runs(text, base = {}) {
  const out = [];
  let bold = false, ital = false, code = false, buf = "";
  const flush = (extra = {}) => {
    if (!buf) return;
    out.push(new TextRun({ text: buf, bold: bold || base.bold, italics: ital || base.italics, font: code ? MONO : (base.font || FONT),
      size: base.size || BODY, color: base.color || INK, ...extra }));
    buf = "";
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i], n = text[i + 1];
    if (!code && c === "*" && n === "*") { flush(); bold = !bold; i++; continue; }
    if (!code && c === "*") { flush(); ital = !ital; continue; }
    if (c === "`") { flush(); code = !code; continue; }
    if (!code && (c === "_" || c === "^") && n === "{") {
      const j = text.indexOf("}", i + 2);
      if (j > 0) {
        flush();
        buf = text.slice(i + 2, j);
        flush(c === "_" ? { subScript: true } : { superScript: true });
        i = j;
        continue;
      }
    }
    buf += c;
  }
  flush();
  return out;
}
function plain(text) {
  return text.replace(/\*\*/g, "").replace(/\*/g, "").replace(/`/g, "").replace(/[_^]\{([^}]*)\}/g, "$1");
}

// ---------- helpers -------------------------------------------------------------------------------------------------
let listInstance = 0;
const para = (text, opts = {}) => new Paragraph({
  children: runs(text, opts.run || {}), spacing: { after: opts.after ?? 120, before: opts.before ?? 0, line: opts.line ?? 276 },
  alignment: opts.align || AlignmentType.JUSTIFIED, keepNext: opts.keepNext, keepLines: opts.keepLines, indent: opts.indent,
  shading: opts.shading,
});
const cellBorders = { top: { style: BorderStyle.SINGLE, size: 4, color: RULE }, bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE },
  left: { style: BorderStyle.SINGLE, size: 4, color: RULE }, right: { style: BorderStyle.SINGLE, size: 4, color: RULE } };

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20), data: b };
}

function table(block) {
  const total = block.widths.reduce((a, b) => a + b, 0);
  const widths = block.widths.map(w => Math.floor((w / total) * CW));
  widths[widths.length - 1] += CW - widths.reduce((a, b) => a + b, 0);
  const sz = Math.round((block.font || 9) * 2);
  const mk = (txt, i, header) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders: cellBorders, verticalAlign: VerticalAlign.CENTER,
    shading: header ? { type: ShadingType.CLEAR, color: "auto", fill: "DCE6F1" } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ children: runs(String(txt), { size: sz, bold: header }), spacing: { after: 0, line: 240 },
      alignment: AlignmentType.LEFT })],
  });
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: block.header.map((h, i) => mk(h, i, true)) })];
  block.rows.forEach((r, k) => rows.push(new TableRow({ cantSplit: true, children: r.map((c, i) => {
    const cell = mk(c, i, false);
    return cell;
  }) })));
  const out = [];
  out.push(new Paragraph({ children: [new TextRun({ text: `Table ${block.label}. `, bold: true, font: FONT, size: 19, color: ACCENT }),
    ...runs(block.caption, { size: 19 })], spacing: { before: 160, after: 80, line: 252 }, keepNext: true, alignment: AlignmentType.LEFT }));
  out.push(new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: widths, rows }));
  if (block.note) out.push(para(block.note, { run: { size: 17, italics: true, color: MUTED }, before: 60, after: 160, align: AlignmentType.LEFT }));
  else out.push(new Paragraph({ children: [], spacing: { after: 120 } }));
  return out;
}

function figure(block) {
  const img = pngSize(path.join(ROOT, block.path));
  const wpx = Math.round((block.width || 6.3) * 96);
  const hpx = Math.round(wpx * img.h / img.w);
  return [
    new Paragraph({ children: [new ImageRun({ type: "png", data: img.data, transformation: { width: wpx, height: hpx },
      altText: { title: `Figure ${block.label}`, description: plain(block.caption), name: `fig${block.label}` } })],
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true }),
    new Paragraph({ children: [new TextRun({ text: `Fig. ${block.label}. `, bold: true, font: FONT, size: 18, color: ACCENT }),
      ...runs(block.caption, { size: 18, color: "333333" })], spacing: { after: 200, line: 240 }, alignment: AlignmentType.LEFT }),
  ];
}

function box(block) {
  const fills = { understand: "EAF2FB", info: "F2F2F2", good: "E8F5EC", bad: "FCEDE8" };
  const edge = { understand: "2A78D6", info: "7F7F7F", good: "1BAF7A", bad: "C0504D" };
  const kids = [new Paragraph({ children: runs(block.title, { bold: true, size: 21, color: ACCENT }), spacing: { after: 80 } })];
  for (const it of block.items) {
    kids.push(new Paragraph({ children: runs(it, { size: 20 }), numbering: { reference: "bullets", level: 0 },
      spacing: { after: 60, line: 264 } }));
  }
  const b = { style: BorderStyle.SINGLE, size: 8, color: edge[block.kind] || "7F7F7F" };
  return [new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW], rows: [new TableRow({ cantSplit: false,
    children: [new TableCell({ width: { size: CW, type: WidthType.DXA }, borders: { top: b, bottom: b, left: { ...b, size: 24 }, right: b },
      shading: { type: ShadingType.CLEAR, color: "auto", fill: fills[block.kind] || "F2F2F2" },
      margins: { top: 120, bottom: 120, left: 180, right: 180 }, children: kids })] })] }),
  new Paragraph({ children: [], spacing: { after: 160 } })];
}

function code(block) {
  const out = [];
  if (block.title) out.push(new Paragraph({ children: runs(block.title, { bold: true, size: 19, color: ACCENT }),
    spacing: { before: 120, after: 60 }, keepNext: true }));
  block.lines.forEach((ln, k) => out.push(new Paragraph({
    children: [new TextRun({ text: ln.length ? ln : " ", font: MONO, size: 16, color: INK })],
    shading: { type: ShadingType.CLEAR, color: "auto", fill: "F4F4F2" }, spacing: { after: 0, line: 230 },
    keepNext: k < block.lines.length - 1, keepLines: true, indent: { left: 120, right: 120 }, alignment: AlignmentType.LEFT,
  })));
  out.push(new Paragraph({ children: [], spacing: { after: 140 } }));
  return out;
}

function heading(block) {
  const lv = { h1: HeadingLevel.HEADING_1, h2: HeadingLevel.HEADING_2, h3: HeadingLevel.HEADING_3 }[block.t];
  return new Paragraph({ heading: lv, children: runs(block.text, { bold: true, font: FONT,
    size: { h1: 30, h2: 24, h3: 22 }[block.t], color: ACCENT }) });
}

function toc() {
  const out = [new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, font: FONT, size: 30, color: ACCENT })],
    spacing: { before: 0, after: 200 }, pageBreakBefore: true })];
  for (const b of content) {
    if (b.t !== "h1" && b.t !== "h2") continue;
    if (b.text === "Summary") continue;
    const pg = tocPages[plain(b.text)] ?? "";
    out.push(new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: CW, leader: "dot" }],
      indent: { left: b.t === "h2" ? 360 : 0 }, spacing: { after: b.t === "h1" ? 50 : 20, before: b.t === "h1" ? 80 : 0 },
      children: [new TextRun({ text: plain(b.text), font: FONT, size: b.t === "h1" ? 20 : 19, bold: b.t === "h1", color: INK }),
        new TextRun({ text: `\t${pg}`, font: FONT, size: 19, color: INK })],
    }));
  }
  return out;
}

function titlePage(b) {
  return [
    new Paragraph({ children: [], spacing: { before: 2400 } }),
    new Paragraph({ children: [new TextRun({ text: b.title, font: FONT, size: 60, bold: true, color: ACCENT })],
      alignment: AlignmentType.LEFT, spacing: { after: 120 } }),
    new Paragraph({ children: [new TextRun({ text: b.subtitle, font: FONT, size: 36, color: INK })],
      spacing: { after: 360 }, border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: ACCENT, space: 8 } } }),
    ...b.lines.map((l, i) => new Paragraph({ children: [new TextRun({ text: l, font: FONT, size: i === 1 ? 20 : 22, color: INK })],
      spacing: { after: 140 } })),
    new Paragraph({ children: [], spacing: { before: 2400 } }),
    para(b.note, { run: { size: 18, italics: true, color: MUTED }, align: AlignmentType.LEFT }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ---------- assemble -----------------------------------------------------------------------------------------------
const children = [];
for (const b of content) {
  switch (b.t) {
    case "title": children.push(...titlePage(b)); break;
    case "h1": case "h2": case "h3": children.push(heading(b)); break;
    case "p": {
      const st = b.style === "small" ? { run: { size: 18, color: MUTED } } : b.style === "ref" ?
        { run: { size: 18 }, indent: { left: 400, hanging: 400 }, after: 70, align: AlignmentType.LEFT } : {};
      children.push(para(b.text, st)); break;
    }
    case "bullets": case "numbered": {
      listInstance++;
      for (const it of b.items) children.push(new Paragraph({ children: runs(it),
        numbering: { reference: b.t === "bullets" ? "bullets" : "numbers", level: 0, instance: listInstance },
        spacing: { after: 70, line: 276 }, alignment: AlignmentType.JUSTIFIED }));
      children.push(new Paragraph({ children: [], spacing: { after: 60 } }));
      break;
    }
    case "eq": children.push(new Paragraph({ children: runs(b.text, { font: "Cambria Math", size: 21 }), alignment: AlignmentType.CENTER,
      spacing: { before: 100, after: 140 } })); break;
    case "code": children.push(...code(b)); break;
    case "box": children.push(...box(b)); break;
    case "figure": children.push(...figure(b)); break;
    case "table": children.push(...table(b)); break;
    case "toc": children.push(...toc()); break;
    case "pagebreak": children.push(new Paragraph({ children: [new PageBreak()] })); break;
    default: throw new Error("unknown block " + b.t);
  }
}

const hstyle = (size, before, after) => ({ run: { font: FONT, size, bold: true, color: ACCENT },
  paragraph: { spacing: { before, after }, keepNext: true, keepLines: true } });
const doc = new Document({
  creator: "Group 14", title: "The Last Rescue: final report", description: "Fundamentals of AI project report",
  styles: {
    default: { document: { run: { font: FONT, size: BODY, color: INK } },
      title: hstyle(60, 0, 120),
      heading1: hstyle(30, 360, 140), heading2: hstyle(24, 240, 100), heading3: hstyle(22, 200, 80) },
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 260 } } } }] },
    { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 400, hanging: 300 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } },
      titlePage: true },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "The Last Rescue: Learning to Cooperate Under Resource Scarcity · Group 14", font: FONT, size: 16, color: MUTED })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: MUTED })] })] }),
      first: new Footer({ children: [new Paragraph({ children: [] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(path.join(ROOT, "report", "report.docx"), buf);
  console.log(`report/report.docx written (${children.length} top-level elements; toc pages: ${Object.keys(tocPages).length})`);
});
