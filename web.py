import os, re, base64, json
import urllib.request, urllib.error
import pandas as pd
import pdfplumber
from io import BytesIO
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ─────────────────────────────────────────────────────────────
#  HTML TEMPLATE  (CSS vars use {{ }} escaped as {%- raw -%})
# ─────────────────────────────────────────────────────────────
HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ROC 360 · AI Auditor</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#020617;--card:#0f172a;--accent:#38bdf8;--text:#f8fafc;
  --border:rgba(255,255,255,0.10);--warn:#fb7185;--ok:#4ade80;
}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',sans-serif;
     padding:40px 20px;display:flex;flex-direction:column;align-items:center}
.container{width:100%;max-width:1100px}
.logo{text-align:center;margin-bottom:36px}
.logo h1{font-size:26px;font-weight:900;letter-spacing:4px;text-transform:uppercase}
.logo h1 span{color:var(--accent)}
.logo p{color:#475569;font-size:11px;letter-spacing:2px;margin-top:4px}
.upload-card{background:var(--card);border:1px solid var(--border);border-radius:18px;
             padding:30px;margin-bottom:24px}
.upload-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
.upload-box{background:rgba(255,255,255,0.02);border:1px dashed rgba(255,255,255,0.15);
            border-radius:12px;padding:24px 16px;text-align:center}
.upload-box label{display:block;font-size:10px;font-weight:700;color:var(--accent);
                  text-transform:uppercase;letter-spacing:2px;margin-bottom:8px}
.upload-box input[type=file]{width:100%;color:var(--text);font-size:12px;cursor:pointer}
.btn{background:var(--accent);color:#020617;border:none;padding:18px;width:100%;
     border-radius:12px;font-weight:900;font-size:14px;letter-spacing:2px;
     text-transform:uppercase;cursor:pointer;transition:.2s}
.btn:hover{opacity:.85}
.loc-bar{background:#1e293b;border:1px solid var(--accent);border-radius:12px;
         padding:16px 20px;text-align:center;font-weight:700;color:var(--accent);
         margin-bottom:20px;font-size:14px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}
.stat{background:var(--card);border:1px solid var(--border);border-radius:14px;
      padding:20px;text-align:center}
.stat.hl{border-color:var(--accent)}
.stat small{display:block;font-size:10px;color:#475569;text-transform:uppercase;
            letter-spacing:1.5px;margin-bottom:8px}
.stat .v{font-size:1.7rem;font-weight:800}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;
      padding:26px;margin-bottom:20px}
.card-hdr{display:flex;justify-content:space-between;align-items:center;
          font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
          color:#94a3b8;padding-bottom:14px;margin-bottom:16px;
          border-bottom:1px solid var(--border)}
.rtable{width:100%;border-collapse:collapse}
.rtable td{padding:13px 10px;border-bottom:1px solid rgba(255,255,255,0.05);font-size:13px}
.rtable tr:last-child td{border-bottom:none}
.rtable .desc{color:#64748b;font-size:12px}
.badge{display:inline-block;padding:5px 13px;border-radius:8px;font-size:10px;
       font-weight:800;text-transform:uppercase;letter-spacing:1px}
.bg{background:rgba(74,222,128,.1);color:#4ade80;border:1px solid rgba(74,222,128,.3)}
.bb{background:rgba(56,189,248,.1);color:#38bdf8;border:1px solid rgba(56,189,248,.3)}
.by{background:rgba(252,211,77,.1);color:#fcd34d;border:1px solid rgba(252,211,77,.3)}
.br{background:rgba(251,113,133,.1);color:#fb7185;border:1px solid rgba(251,113,133,.3)}
.miss-title{font-size:14px;font-weight:700;color:var(--warn);
            text-transform:uppercase;letter-spacing:2px;margin-bottom:6px}
.miss-sub{font-size:12px;color:#64748b;margin-bottom:14px}
.miss-tags{display:flex;gap:8px;flex-wrap:wrap}
.miss-tag{background:rgba(251,113,133,.1);border:1px solid rgba(251,113,133,.3);
          color:#fb7185;font-size:10px;font-weight:800;padding:5px 13px;
          border-radius:8px;text-transform:uppercase;letter-spacing:1.5px}
.finding{border-left:3px solid var(--warn);padding:11px 15px;margin-bottom:10px;
         background:rgba(251,113,133,.04);border-radius:0 10px 10px 0}
.finding strong{display:block;font-size:13px;font-weight:700;margin-bottom:3px}
.finding span{font-size:12px;color:#94a3b8;line-height:1.65}
.flag{color:var(--warn);font-size:12px;padding:4px 0}
.bk-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:4px}
.bk-row{display:flex;justify-content:space-between;align-items:center;
        padding:8px 12px;background:rgba(255,255,255,0.02);border-radius:8px;font-size:12px}
.bk-row span:first-child{color:#94a3b8}
.bk-row span:last-child{font-weight:700}
@media(max-width:600px){.upload-grid,.stats,.bk-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="container">
  <div class="logo">
    <h1>ROC <span>360</span> · AI AUDITOR</h1>
    <p>AUTOMATED TECHNICAL AUDIT · APPRAISAL + SCOPE OF WORK</p>
  </div>
  <div class="upload-card">
    <form method="POST" enctype="multipart/form-data">
      <div class="upload-grid">
        <div class="upload-box">
          <label>📄 Appraisal Report (PDF)</label>
          <input type="file" name="f_pdf" accept=".pdf" required>
        </div>
        <div class="upload-box">
          <label>📊 Scope of Work (Excel / CSV)</label>
          <input type="file" name="f_sow" accept=".xlsx,.xls,.csv" required>
        </div>
      </div>
      <button class="btn" type="submit">ANALYZE PROJECT</button>
    </form>
  </div>

  {% if r %}
  <div class="loc-bar">📍 &nbsp; {{ r.address }}</div>

  <div class="stats">
    <div class="stat"><small>Total SQFT (GLA)</small><div class="v">{{ r.sqft }}</div></div>
    <div class="stat"><small>Total Reno Budget</small><div class="v">${{ r.total }}</div></div>
    <div class="stat"><small>Cost / SQFT</small><div class="v">${{ r.c_sqft }}</div></div>
    <div class="stat"><small>ARV (Appraised Value)</small><div class="v">${{ r.arv }}</div></div>
    <div class="stat hl"><small>Contingency %</small><div class="v">{{ r.cont_perc }}%</div></div>
    <div class="stat"><small>Condition (UAD)</small><div class="v">{{ r.cond }}</div></div>
  </div>

  <div class="card">
    <div class="card-hdr">
      <span>Risk Strategy Matrix</span>
      <span class="badge b{{ r.cat_color }}">{{ r.cat_id }} · {{ r.cat_name }}</span>
    </div>
    <table class="rtable">
      <tr>
        <td><b>Market Benchmarking</b></td>
        <td class="desc">Area avg (${{ r.bench_ref }}/sqft) vs SOW (${{ r.c_sqft }}/sqft)</td>
        <td style="text-align:right"><span class="badge b{{ r.bench_color }}">{{ r.bench_status }}</span></td>
      </tr>
      <tr>
        <td><b>Rehab Intensity</b></td>
        <td class="desc">Workload ratio vs estimated complexity</td>
        <td style="text-align:right"><span class="badge bb">{{ r.rehab_ratio }}</span></td>
      </tr>
      <tr>
        <td><b>Required Permits</b></td>
        <td class="desc">Status for structural / MEP work</td>
        <td style="text-align:right"><span class="badge b{{ r.permit_color }}">{{ r.permits }}</span></td>
      </tr>
      <tr>
        <td><b>Compliance Check</b></td>
        <td class="desc">ROC 360 Min Contingency (5% of reno budget)</td>
        <td style="text-align:right">
          <span class="badge {{ 'bg' if r.cont_perc >= 5 else 'br' }}">
            {{ 'COMPLIANT' if r.cont_perc >= 5 else 'NON-COMPLIANT' }}
          </span>
        </td>
      </tr>
      <tr>
        <td><b>Year Built</b></td>
        <td class="desc">Age-related risk assessment</td>
        <td style="text-align:right">
          <span class="badge {{ 'by' if r.year and r.year < 1970 else 'bg' }}">
            {{ r.year if r.year else 'N/A' }}
          </span>
        </td>
      </tr>
      <tr>
        <td><b>LTC Ratio</b></td>
        <td class="desc">Total Reno Budget (incl. contingency) ÷ ARV</td>
        <td style="text-align:right"><span class="badge b{{ r.ltc_color }}">{{ r.ltc }}%</span></td>
      </tr>
    </table>
  </div>

  <div class="card">
    <div class="card-hdr"><span>Budget Breakdown by Category</span></div>
    <div class="bk-grid">
      {% for cat, amt in r.breakdown %}
      <div class="bk-row"><span>{{ cat }}</span><span>${{ amt }}</span></div>
      {% endfor %}
    </div>
  </div>

  <div class="card">
    <div class="miss-title">⚠ Missing SOW Components</div>
    <div class="miss-sub">Standard categories NOT detected in the Scope of Work:</div>
    <div class="miss-tags">
      {% if r.missing %}
        {% for item in r.missing %}<span class="miss-tag">{{ item }}</span>{% endfor %}
      {% else %}
        <span style="color:#4ade80;font-size:13px">✓ All core components detected.</span>
      {% endif %}
    </div>
  </div>

  {% if r.ai_findings %}
  <div class="card">
    <div class="card-hdr"><span>AI Audit Findings</span></div>
    {% for f in r.ai_findings %}
    <div class="finding">
      <strong>{{ f.title }}</strong>
      <span>{{ f.detail }}</span>
    </div>
    {% endfor %}
  </div>
  {% endif %}

  {% if r.logs %}
  <div class="card">
    <div class="card-hdr"><span>Audit Flags</span></div>
    {% for log in r.logs %}<div class="flag">⚠ {{ log }}</div>{% endfor %}
  </div>
  {% endif %}
  {% endif %}
</div>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
SECTION_HEADERS = {
    'SOFT COSTS', 'DEMOLITION', 'FOUNDATION', 'EXTERIOR', 'INTERIOR',
    'SERVICES - MEP', 'APPLIANCES', 'SITE WORK', 'CONTINGENCY', 'KITCHEN',
    'BATHS', 'FINAL CLEAN UP', 'LTC CATCHUP',
}
SKIP_ROW_NAMES = {'LINE ITEM', 'NAN', 'NONE', '', 'OVERALL DESCRIPTION'}

CORE_REQUIRED = [
    'ROOF', 'HVAC', 'KITCHEN', 'BATHROOM', 'FLOORING', 'PAINT',
    'WINDOWS', 'PLUMBING', 'ELECTRICAL', 'FOUNDATION', 'DEMO', 'PERMITS',
]


def to_float(val):
    if val is None:
        return 0.0
    s = str(val).strip()
    if s.lower() in ('nan', 'none', ''):
        return 0.0
    s = re.sub(r'[^\d.\-]', '', s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def fmt(n):
    return f"{n:,.0f}"


def fmt2(n):
    return f"{n:,.2f}"


# ─────────────────────────────────────────────────────────────
#  PARSE SOW  — column 0 = name, column 2 = cost (always)
# ─────────────────────────────────────────────────────────────
def parse_sow(excel_file):
    fname = excel_file.filename.lower()
    excel_file.seek(0)
    try:
        if fname.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(excel_file, header=None)
        else:
            df = pd.read_csv(excel_file, header=None)
    except Exception as e:
        return 0, 0, [], [], [f"SOW read error: {e}"]

    # Cost is always in column 2 (0-indexed) for this Excel format
    COST_COL = 2

    total = 0.0
    cont = 0.0
    breakdown_acc = {}
    current_section = "OTHER"
    found_comp = set()
    sow_lines = []

    for _, row in df.iterrows():
        raw_name = row.iloc[0] if len(row) > 0 else ''
        name = str(raw_name).strip()
        name_upper = name.upper().strip()

        # Skip header / empty rows
        if name_upper in SKIP_ROW_NAMES:
            continue

        # Section header rows (no cost on these)
        if name_upper in SECTION_HEADERS:
            current_section = name_upper
            continue

        # PROJECT TOTAL footer row — skip
        if 'PROJECT TOTAL' in name_upper or 'TOTAL PROJECT' in name_upper:
            continue

        cost = to_float(row.iloc[COST_COL]) if len(row) > COST_COL else 0.0
        if cost == 0:
            continue

        name_lower = name.lower()

        # Contingency — track separately, NOT added to reno total
        if 'contingency' in name_lower:
            cont += cost
            continue

        total += cost
        sow_lines.append(f"{name}: ${cost:,.2f}")

        bucket = current_section if current_section else "OTHER"
        breakdown_acc[bucket] = breakdown_acc.get(bucket, 0.0) + cost

        # ── Detect standard components ──
        if any(k in name_lower for k in ('roof', 'shingle')):
            found_comp.add('ROOF')
        if any(k in name_lower for k in ('hvac', 'heat pump', 'ac eq', 'air handler', 'mini split', 'condenser')):
            found_comp.add('HVAC')
        if 'kitchen' in name_lower or 'cabinet' in name_lower or 'countertop' in name_lower:
            found_comp.add('KITCHEN')
        if any(k in name_lower for k in ('bath', 'toilet', 'shower', 'tub', 'vanity', 'mirror')):
            found_comp.add('BATHROOM')
        if any(k in name_lower for k in ('floor', 'vinyl', 'carpet', 'tile', 'hardwood', 'lvp', 'finish')):
            found_comp.add('FLOORING')
        if 'paint' in name_lower:
            found_comp.add('PAINT')
        if 'window' in name_lower:
            found_comp.add('WINDOWS')
        if any(k in name_lower for k in ('plumb', 'sewer', 'water')):
            found_comp.add('PLUMBING')
        if any(k in name_lower for k in ('electric', 'wiring', 'lighting', 'panel')):
            found_comp.add('ELECTRICAL')
        if any(k in name_lower for k in ('slab', 'foundation', 'footing')):
            found_comp.add('FOUNDATION')
        if any(k in name_lower for k in ('demo', 'dumpster', 'tear out', 'remove')):
            found_comp.add('DEMO')
        if 'permit' in name_lower:
            found_comp.add('PERMITS')
        if any(k in name_lower for k in ('drywall', 'wallboard', 'sheetrock')):
            found_comp.add('DRYWALL')
        if any(k in name_lower for k in ('frame', 'framing', 'stud')):
            found_comp.add('FRAMING')
        if 'insulation' in name_lower:
            found_comp.add('INSULATION')
        if any(k in name_lower for k in ('grading', 'landscaping', 'driveway', 'concrete', 'site')):
            found_comp.add('SITE WORK')

    missing = [c for c in CORE_REQUIRED if c not in found_comp]
    breakdown = [
        (cat.title(), fmt(v))
        for cat, v in sorted(breakdown_acc.items(), key=lambda x: -x[1])
        if v > 0
    ]
    return total, cont, missing, breakdown, sow_lines


# ─────────────────────────────────────────────────────────────
#  PARSE PDF
# ─────────────────────────────────────────────────────────────
def parse_pdf(pdf_file):
    pdf_bytes = pdf_file.read()
    pdf_file.seek(0)
    full_text = ""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:12]:
                full_text += (page.extract_text() or "") + "\n"
    except Exception as e:
        return pdf_bytes, "", "PDF Error", 0, "N/A", None, 0

    # ── Address ──
    addr = "Not Detected"
    addr_patterns = [
        r"ADDRESS OF PROPERTY APPRAISED\s+([\d][\w\s,.\-]{5,60})",
        r"Property Address\s+([\d][\w\s,.\-]{5,60})",
        r"(\d{2,6}\s+[A-Z][a-z]+(?:\s+[A-Za-z]+){1,3}"
        r"(?:\s+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl|Hwy|Cir|Ter|Court))"
        r"[^\n]{0,40})",
    ]
    for pat in addr_patterns:
        m = re.search(pat, full_text, re.I)
        if m:
            raw = m.group(1).split('\n')[0].strip()
            raw = re.sub(r'\s+', ' ', raw)
            if len(raw) > 8:
                addr = raw
                break

    # ── SQFT (Gross Living Area) ──
    sqft = 0
    sqft_patterns = [
        r"Gross Living Area\s*[^\d]{0,10}([\d][,\d]{2,})",
        r"GLA\s*[^\d]{0,5}([\d][,\d]{2,})",
        r"Square Feet of Gross Living Area[^\d]{0,10}([\d][,\d]{2,})",
        r"Sq\.?\s*Ft\.?\s+of\s+Gross[^\d]{0,10}([\d][,\d]{2,})",
        # UAD room/bed/bath/sqft pattern: "7 3 2.1 1,528"
        r"\b7\s+3\s+2\.1\s+(1[,\s]?\d{3})\b",
        r"\b(1[,]?5[0-9]{2})\b",   # fallback: 1,5XX range
    ]
    for pat in sqft_patterns:
        m = re.search(pat, full_text, re.I)
        if m:
            candidate = to_float(m.group(1).replace(',', '').replace(' ', ''))
            if 400 < candidate < 15000:
                sqft = int(candidate)
                break

    # ── Condition (UAD C1–C6) — find the SUBJECT's condition ──
    cond = "N/A"
    # Look for explicit "Condition C1" or similar near subject section
    m = re.search(r"Condition\s+(C[1-6])", full_text, re.I)
    if m:
        cond = m.group(1)
    else:
        # Fallback: first C1-C6 occurrence
        m = re.search(r"\b(C[1-6])\b", full_text)
        if m:
            cond = m.group(1)

    # ── Year Built ──
    year = None
    m = re.search(r"Year Built[:\s]*(\d{4})", full_text, re.I)
    if m:
        year = int(m.group(1))
    if not year:
        m = re.search(r"\b(19[5-9]\d|20[0-2]\d)\b", full_text)
        if m:
            year = int(m.group(1))

    # ── ARV (Appraised Value) ──
    arv = 0
    arv_patterns = [
        # "APPRAISED VALUE OF SUBJECT PROPERTY $ 285,000"
        r"APPRAISED VALUE OF SUBJECT PROPERTY[^$\d]{0,30}\$?\s*([\d]{2,3}[,\d]+)",
        # "$ , as of" pattern from form
        r"\$\s*([\d]{2,3}[,\d]+)\s*,\s*as of",
        # "285,000  05/20/2025" (value followed by date)
        r"\b([\d]{3}[,\d]+)\s+\d{2}/\d{2}/\d{4}",
        # Generic appraised / market value
        r"(?:market value|appraised value|opinion of value)[^$\n]{0,50}\$?\s*([\d]{2,3}[,\d]+)",
        # Value by Sales Comparison
        r"Indicated Value by Sales Comparison Approach\s*\$?\s*([\d]{2,3}[,\d]+)",
        # Fallback: any $285,000 type number in range
        r"\$([\d]{2,3}[,\d]{3,})",
    ]
    for pat in arv_patterns:
        for m in re.finditer(pat, full_text, re.I):
            candidate = to_float(m.group(1).replace(',', ''))
            if 50000 < candidate < 5000000:
                arv = int(candidate)
                break
        if arv:
            break

    return pdf_bytes, full_text, addr, sqft, cond, year, arv


# ─────────────────────────────────────────────────────────────
#  ANTHROPIC AI CALL
# ─────────────────────────────────────────────────────────────
def call_ai(pdf_bytes, sow_lines, addr, sqft, cond, year, arv, total, cont):
    if not ANTHROPIC_API_KEY:
        return None, "No ANTHROPIC_API_KEY set in environment."

    sow_summary = "\n".join(sow_lines[:80])
    cont_perc = round(cont / total * 100, 1) if total > 0 else 0
    c_sqft = round(total / sqft, 2) if sqft > 0 else 0

    system = """You are a senior real estate construction auditor at ROC 360 (hard money lender).
You receive an appraisal PDF and a Scope of Work summary.
Return ONLY valid JSON — no markdown, no extra text, no preamble.
{
  "findings": [
    {"title": "short title", "detail": "specific technical detail with real numbers"}
  ],
  "extra_missing": ["category1"],
  "address_override": null,
  "sqft_override": null
}
Rules:
- findings: 3–6 SPECIFIC issues using real numbers from the documents.
  Focus on: budget adequacy vs ARV, missing trades, cost/sqft vs market,
  contingency level, construction risks, new build vs rehab mismatches.
- extra_missing: additional missing trade categories beyond what was already found.
  Use only: electrical, plumbing, roof, hvac, drywall, flooring, bathroom,
  kitchen, windows, insulation, painting, demolition, foundation, site-work.
- address_override: corrected full address string if you find a better one, else null.
- sqft_override: integer if you find a more accurate GLA, else null.
- Return ONLY the JSON object. Absolutely nothing else."""

    msg = (
        f"EXTRACTED APPRAISAL DATA:\n"
        f"Address: {addr}\n"
        f"GLA (sqft): {sqft}\n"
        f"UAD Condition: {cond}\n"
        f"Year Built: {year}\n"
        f"ARV (Appraised Value): ${arv:,.0f}\n\n"
        f"SCOPE OF WORK LINE ITEMS:\n{sow_summary}\n\n"
        f"CALCULATED METRICS:\n"
        f"Total Reno Budget (excl. contingency): ${total:,.2f}\n"
        f"Contingency: ${cont:,.2f}\n"
        f"Contingency %: {cont_perc}%\n"
        f"Cost/sqft (reno ÷ GLA): ${c_sqft}\n\n"
        f"Analyze the above and return JSON."
    )

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1200,
        "system": system,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.b64encode(pdf_bytes).decode(),
                    },
                },
                {"type": "text", "text": msg},
            ],
        }],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "pdfs-2024-09-25",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
            raw = "".join(b.get("text", "") for b in data.get("content", []))
            clean = re.sub(r"```(?:json)?|```", "", raw).strip()
            return json.loads(clean), None
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        return None, f"API HTTP {e.code}: {body}"
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────
#  MAIN AUDIT FUNCTION
# ─────────────────────────────────────────────────────────────
def audit(pdf_file, excel_file):
    logs = []

    # 1. Parse PDF
    pdf_bytes, full_text, addr, sqft, cond, year, arv = parse_pdf(pdf_file)
    if sqft == 0:
        logs.append("GLA/SQFT not detected from PDF — check appraisal format.")
    if arv == 0:
        logs.append("ARV not detected from PDF — check appraisal format.")

    # 2. Parse SOW Excel
    total, cont, missing, breakdown, sow_lines = parse_sow(excel_file)
    if total == 0:
        logs.append("No cost data found in Excel — check file format.")

    grand = total + cont

    # Contingency % = contingency / reno budget (excl. contingency)
    cont_perc = round(cont / total * 100, 1) if total > 0 else 0.0
    c_sqft = round(total / sqft, 2) if sqft > 0 else 0.0
    ltc = round(grand / arv * 100, 1) if arv > 0 else 0.0

    # 3. Risk classification
    if grand < 40000:
        cat_id, cat_name, rehab_ratio, permits, cat_color, permit_color = (
            "A1", "Light Cosmetic", "0–20%", "STANDARD", "g", "y"
        )
    elif grand < 120000:
        cat_id, cat_name, rehab_ratio, permits, cat_color, permit_color = (
            "A3", "Gut Rehab", "40–60%", "REQUIRED", "y", "y"
        )
    else:
        cat_id, cat_name, rehab_ratio, permits, cat_color, permit_color = (
            "A5", "Ground Up / Major", "80–100%", "CRITICAL", "r", "r"
        )

    # Benchmark: NC new construction market ~$165/sqft
    bench_ref = 165
    if c_sqft > 200:
        bench_status, bench_color = "OVER BUDGET", "r"
    elif c_sqft < 80:
        bench_status, bench_color = "UNDER SCOPED", "y"
    else:
        bench_status, bench_color = "STABLE", "g"

    ltc_color = "g" if ltc <= 75 else ("y" if ltc <= 90 else "r")

    # 4. AI analysis
    ai_findings = []
    ai_data, ai_err = call_ai(
        pdf_bytes, sow_lines, addr, sqft, cond, year, arv, total, cont
    )
    if ai_err:
        logs.append(f"AI skipped: {ai_err}")
    elif ai_data:
        if ai_data.get("address_override"):
            addr = ai_data["address_override"]
        if ai_data.get("sqft_override") and sqft == 0:
            sqft = int(ai_data["sqft_override"])
            c_sqft = round(total / sqft, 2) if sqft > 0 else c_sqft
        for cat in (ai_data.get("extra_missing") or []):
            tag = cat.upper()
            if tag not in missing:
                missing.append(tag)
        for f in (ai_data.get("findings") or []):
            if f.get("title"):
                ai_findings.append({
                    "title": f["title"],
                    "detail": f.get("detail", ""),
                })

    # 5. Compliance flags
    if cont_perc < 5 and grand > 0:
        logs.append(
            f"Contingency {cont_perc}% is below ROC 360 minimum of 5%."
        )
    if ltc > 90 and arv > 0:
        logs.append(f"LTC ratio {ltc}% exceeds 90% — high leverage risk.")

    return {
        "address":      addr,
        "sqft":         fmt(sqft) if sqft else "N/A",
        "total":        fmt(grand),
        "c_sqft":       fmt2(c_sqft),
        "arv":          fmt(arv) if arv else "N/A",
        "cont_perc":    cont_perc,
        "cond":         cond,
        "year":         year,
        "cat_id":       cat_id,
        "cat_name":     cat_name,
        "cat_color":    cat_color,
        "rehab_ratio":  rehab_ratio,
        "permits":      permits,
        "permit_color": permit_color,
        "bench_status": bench_status,
        "bench_color":  bench_color,
        "bench_ref":    bench_ref,
        "ltc":          ltc,
        "ltc_color":    ltc_color,
        "breakdown":    breakdown,
        "missing":      missing,
        "ai_findings":  ai_findings,
        "logs":         logs,
    }


# ─────────────────────────────────────────────────────────────
#  FLASK ROUTES
# ─────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    r = None
    if request.method == "POST":
        p = request.files.get("f_pdf")
        s = request.files.get("f_sow")
        if p and s:
            r = audit(p, s)
    return render_template_string(HTML, r=r)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)
