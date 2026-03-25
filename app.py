import streamlit as st
import openai
import json
import subprocess
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Report Generator",
    page_icon="📊",
    layout="centered"
)

# ── Styles ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { max-width: 800px; margin: 0 auto; }
    .status-box {
        background: #f0f4ff;
        border-left: 4px solid #4a6cf7;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 8px 0;
        font-size: 14px;
    }
    .done-box {
        background: #f0fff4;
        border-left: 4px solid #38a169;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 8px 0;
        font-size: 14px;
    }
    .error-box {
        background: #fff0f0;
        border-left: 4px solid #e53e3e;
        padding: 12px 16px;
        border-radius: 4px;
        margin: 8px 0;
        font-size: 14px;
    }
    h1 { font-size: 1.8rem !important; }
    .hint { font-size: 12px; color: #666; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.title("📊 Market Report Generator")
st.markdown("Enter a market title and get a fully structured research report as a Word file.")

# ── Sidebar: API Key ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    st.markdown('<p class="hint">Your key is never stored. It lives only in this session.</p>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Report format matches:**")
    st.markdown("- Intro paragraph\n- Report Summary\n- Analyst Opinion\n- Definition / Scope\n- Drivers / Restraints / Trends\n- Segmental Analysis\n- Competitive Outlook\n- Key Players\n- Strategic Outlook\n- Scope Table\n- Bibliography\n- FAQs")

# ── Main input ───────────────────────────────────────────────────────────────
title = st.text_input(
    "Market Title",
    placeholder="e.g. Global Electric Vehicle Battery Market",
    help="Be specific. Include the industry and optionally the geography."
)

run_btn = st.button("Generate Report", type="primary", disabled=(not api_key or not title))

# ── Generation logic ─────────────────────────────────────────────────────────
def call_gpt(client, system_prompt, user_prompt, json_mode=True):
    kwargs = dict(
        model="gpt-5.4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
        max_completion_tokens=4096,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if json_mode:
        return json.loads(content)
    return content


SYSTEM_ANALYST = """You are a senior market research analyst. You generate realistic, well-reasoned market data and structured content for professional market research reports. 
All numbers you generate should be internally consistent (CAGR, base year values, forecast year values must all align mathematically). 
Respond ONLY in valid JSON. No markdown, no explanation outside the JSON."""

SYSTEM_WRITER = """You are a professional market research writer producing reports in a formal, analytical, third-person tone. 
Write in complete paragraphs. Be precise, data-driven, and avoid filler phrases. 
Respond ONLY in valid JSON. No markdown fences, no commentary outside the JSON."""


def step1_generate_numbers(client, title):
    prompt = f"""Generate realistic and internally consistent market data for: "{title}"

Return JSON with this exact structure:
{{
  "market_name": "Full market name",
  "tagline": "One sentence describing what the market covers, its segmentation axes, and forecast period (2026-2036)",
  "base_year_value_usd_bn": 0.0,
  "forecast_2026_value_usd_bn": 0.0,
  "forecast_2036_value_usd_bn": 0.0,
  "cagr_pct": 0.0,
  "base_year": 2025,
  "forecast_start": 2026,
  "forecast_end": 2036,
  "segments": {{
    "axis1": {{
      "name": "Segment axis name (e.g. Product Type)",
      "segments": ["Seg A", "Seg B", "Seg C"],
      "leader": "Seg A",
      "leader_share_pct": 0.0
    }},
    "axis2": {{
      "name": "Segment axis name (e.g. End Use Industry)",
      "segments": ["Industry A", "Industry B"],
      "leader": "Industry A",
      "leader_share_pct": 0.0
    }},
    "axis3": {{
      "name": "Segment axis name (e.g. Region / Material / Technology)",
      "segments": ["Seg X", "Seg Y"],
      "leader": "Seg X",
      "leader_share_pct": 0.0
    }}
  }},
  "regions": ["North America", "Latin America", "Western Europe", "Eastern Europe", "East Asia", "South Asia and Pacific", "Middle East and Africa"],
  "key_companies": ["Company A", "Company B", "Company C", "Company D", "Company E", "Company F", "Company G", "Company H", "Company I", "Company J"],
  "analyst_name": "Full Name",
  "analyst_title": "Senior Consultant at FMI"
}}

IMPORTANT: base_year_value * (1 + cagr/100)^10 should approximately equal forecast_2036_value."""
    return call_gpt(client, SYSTEM_ANALYST, prompt)


def step2_generate_content(client, title, numbers):
    n = numbers
    seg1 = n["segments"]["axis1"]
    seg2 = n["segments"]["axis2"]
    seg3 = n["segments"]["axis3"]

    prompt = f"""Write all content sections for a market research report on: "{title}"

Market data to use exactly:
- Market value: USD {n['base_year_value_usd_bn']} billion in {n['base_year']}
- Forecast 2026: USD {n['forecast_2026_value_usd_bn']} billion
- Forecast 2036: USD {n['forecast_2036_value_usd_bn']} billion  
- CAGR: {n['cagr_pct']}% from {n['forecast_start']} to {n['forecast_end']}
- Segment 1 ({seg1['name']}): {seg1['leader']} leads with {seg1['leader_share_pct']}% share in 2026
- Segment 2 ({seg2['name']}): {seg2['leader']} leads with {seg2['leader_share_pct']}% share in 2026
- Segment 3 ({seg3['name']}): {seg3['leader']} leads with {seg3['leader_share_pct']}% share in 2026
- Key companies: {', '.join(n['key_companies'][:7])}
- Analyst: {n['analyst_name']}, {n['analyst_title']}

Return JSON with this exact structure (all values are strings, use \\n for paragraph breaks within a field only if needed):
{{
  "intro_paragraph": "2-sentence overview: what the market covers + the 3 key numbers (base year value, 2036 value, CAGR) + top segment shares",
  
  "summary_snapshot_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "summary_demand_bullets": ["bullet 1 with data citation style", "bullet 2", "bullet 3"],
  "summary_product_bullets": ["bullet 1", "bullet 2", "bullet 3"],
  "summary_geo_bullets": ["bullet on leading end use", "bullet on regions covered", "bullet on key companies"],
  
  "analyst_quote": "One impactful sentence quote from the analyst about the market dynamic",
  
  "definition": "2-3 sentence paragraph defining what this market includes",
  "inclusions": ["inclusion 1", "inclusion 2", "inclusion 3"],
  "exclusions": ["exclusion 1", "exclusion 2", "exclusion 3"],
  "methodology": "2-3 sentence paragraph describing the research methodology",
  
  "drivers_paragraph": "3-4 sentence paragraph on what is driving market growth",
  "restraints_paragraph": "3-4 sentence paragraph on restraints and challenges",
  "trends_paragraph": "3-4 sentence paragraph on key market trends",
  
  "segment1_analysis": "3-4 sentence paragraph analyzing the leading {seg1['name']} segment ({seg1['leader']})",
  "segment2_analysis": "3-4 sentence paragraph analyzing the leading {seg2['name']} segment ({seg2['leader']})",
  "segment3_analysis": "3-4 sentence paragraph analyzing the leading {seg3['name']} segment ({seg3['leader']})",
  
  "competitive_para1": "4-5 sentence paragraph on competitive dynamics, naming 2-3 specific companies with their strategies",
  "competitive_para2": "4-5 sentence paragraph continuing competitive analysis, naming 2-3 more companies",
  
  "strategic_outlook": "3-4 sentence paragraph with FMI's strategic view on the market through 2036",
  
  "bibliography": [
    {{"org": "Organization Name", "year": "2024", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2025", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2024", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2023", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2024", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2025", "title": "Document or report title"}},
    {{"org": "Organization Name", "year": "2024", "title": "Document or report title"}}
  ],
  
  "faqs": [
    {{"q": "How big is the {title.lower()}?", "a": "Answer with base year value and 2036 projection."}},
    {{"q": "What is the CAGR of the {title.lower()}?", "a": "Answer with CAGR and period."}},
    {{"q": "Which {seg1['name'].lower()} leads the {title.lower()}?", "a": "Answer naming the leader and share."}},
    {{"q": "Which {seg2['name'].lower()} leads the {title.lower()}?", "a": "Answer naming the leader and share."}},
    {{"q": "What is driving growth in the {title.lower()}?", "a": "2-sentence answer on key drivers."}},
    {{"q": "Who are the key companies in the {title.lower()}?", "a": "Answer listing top 5-7 companies."}}
  ]
}}"""
    return call_gpt(client, SYSTEM_WRITER, prompt)


def build_docx(numbers, content, output_path):
    """Generate the Word document using the docx npm library via Node.js"""
    n = numbers
    c = content
    seg1 = n["segments"]["axis1"]
    seg2 = n["segments"]["axis2"]
    seg3 = n["segments"]["axis3"]

    # Build bibliography items
    bib_items = "\n".join([
        f'    new Paragraph({{ children: [new TextRun({{ text: " {b["org"]}. {b["year"]}. ", font: "Arial", size: 20 }}), new TextRun({{ text: "{b["title"].replace(chr(34), chr(39))}.", italics: true, font: "Arial", size: 20 }})] }}),'
        for b in c["bibliography"]
    ])

    # Build FAQ paragraphs
    faq_items = "\n".join([
        f'''    new Paragraph({{ children: [new TextRun({{ text: "{faq["q"].replace(chr(34), chr(39))}", bold: true, font: "Arial", size: 22 }})] }}),
    new Paragraph({{ children: [new TextRun({{ text: "{faq["a"].replace(chr(34), chr(39))}", font: "Arial", size: 22 }})] }}),
    new Paragraph({{ children: [new TextRun("")] }}),'''
        for faq in c["faqs"]
    ])

    # Build bullet helpers
    def bullets_js(items, ref):
        return "\n".join([
            f'    new Paragraph({{ numbering: {{ reference: "{ref}", level: 0 }}, children: [new TextRun({{ text: "{item.replace(chr(34), chr(39))}", font: "Arial", size: 22 }})] }}),'
            for item in items
        ])

    summary_snapshot = bullets_js(c["summary_snapshot_bullets"], "bullets-1")
    summary_demand = bullets_js(c["summary_demand_bullets"], "bullets-2")
    summary_product = bullets_js(c["summary_product_bullets"], "bullets-3")
    summary_geo = bullets_js(c["summary_geo_bullets"], "bullets-4")
    inclusions = bullets_js(c["inclusions"], "bullets-5")
    exclusions = bullets_js(c["exclusions"], "bullets-6")
    key_players = bullets_js([co for co in n["key_companies"]], "bullets-7")

    scope_rows = [
        ("Market Value", f"USD {n['base_year_value_usd_bn']} billion in {n['base_year']} to USD {n['forecast_2036_value_usd_bn']} billion by {n['forecast_end']}"),
        ("CAGR", f"{n['cagr_pct']}% from {n['forecast_start']} to {n['forecast_end']}"),
        ("Base Year", str(n["base_year"])),
        ("Forecast Period", f"{n['forecast_start']} to {n['forecast_end']}"),
        (seg1["name"] + " Segmentation", ", ".join(seg1["segments"])),
        (seg2["name"] + " Segmentation", ", ".join(seg2["segments"])),
        (seg3["name"] + " Segmentation", ", ".join(seg3["segments"])),
        ("Regions Covered", ", ".join(n["regions"])),
    ]

    def scope_row_js(label, value, is_header=False):
        bg = "E8F0FE" if is_header else "FFFFFF"
        bold = "true" if is_header else "false"
        return f"""new TableRow({{
      children: [
        new TableCell({{
          borders: {{ top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder }},
          width: {{ size: 3120, type: WidthType.DXA }},
          shading: {{ fill: "{bg}", type: ShadingType.CLEAR }},
          margins: {{ top: 80, bottom: 80, left: 120, right: 120 }},
          children: [new Paragraph({{ children: [new TextRun({{ text: "{label.replace(chr(34), chr(39))}", bold: {bold}, font: "Arial", size: 20 }})] }})]
        }}),
        new TableCell({{
          borders: {{ top: cellBorder, bottom: cellBorder, left: cellBorder, right: cellBorder }},
          width: {{ size: 6240, type: WidthType.DXA }},
          shading: {{ fill: "{bg}", type: ShadingType.CLEAR }},
          margins: {{ top: 80, bottom: 80, left: 120, right: 120 }},
          children: [new Paragraph({{ children: [new TextRun({{ text: "{value.replace(chr(34), chr(39))}", font: "Arial", size: 20 }})] }})]
        }})
      ]
    }})"""

    scope_rows_js = ",\n".join([
        scope_row_js("Metric", "Value", is_header=True),
        *[scope_row_js(label, value) for label, value in scope_rows]
    ])

    def escape(s):
        return s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace('"', "'").replace("\n", " ")

    def h1(text):
        return f'new Paragraph({{ heading: HeadingLevel.HEADING_1, children: [new TextRun({{ text: "{escape(text)}", font: "Arial", size: 32, bold: true }})] }}),'

    def h2(text):
        return f'new Paragraph({{ heading: HeadingLevel.HEADING_2, children: [new TextRun({{ text: "{escape(text)}", font: "Arial", size: 26, bold: true }})] }}),'

    def para(text, bold=False):
        return f'new Paragraph({{ children: [new TextRun({{ text: "{escape(text)}", font: "Arial", size: 22, bold: {"true" if bold else "false"} }})] }}),'

    def spacer():
        return 'new Paragraph({ children: [new TextRun("")] }),'

    js_code = f"""
const {{
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, LevelFormat, BorderStyle, WidthType,
  ShadingType, PageNumber
}} = require('docx');
const fs = require('fs');

const cellBorder = {{ style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" }};

const doc = new Document({{
  numbering: {{
    config: [
      { ", ".join([f'{{ reference: "bullets-{i}", levels: [{{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: {{ paragraph: {{ indent: {{ left: 720, hanging: 360 }} }} }} }}] }}' for i in range(1, 9)]) }
    ]
  }},
  styles: {{
    default: {{ document: {{ run: {{ font: "Arial", size: 22 }} }} }},
    paragraphStyles: [
      {{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: {{ size: 32, bold: true, font: "Arial", color: "1F3864" }},
        paragraph: {{ spacing: {{ before: 320, after: 160 }}, outlineLevel: 0 }} }},
      {{ id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: {{ size: 26, bold: true, font: "Arial", color: "2E5096" }},
        paragraph: {{ spacing: {{ before: 240, after: 120 }}, outlineLevel: 1 }} }},
    ]
  }},
  sections: [{{
    properties: {{
      page: {{
        size: {{ width: 12240, height: 15840 }},
        margin: {{ top: 1440, right: 1440, bottom: 1440, left: 1440 }}
      }}
    }},
    children: [
      // ── Intro paragraph ───────────────────────────────────────────────
      {para(escape(c["intro_paragraph"]))}
      {spacer()}

      // ── Report Summary ────────────────────────────────────────────────
      {h1("Report Summary")}
      {h2("Market Snapshot")}
      {summary_snapshot}
      {spacer()}
      {h2("Demand and Growth Drivers")}
      {summary_demand}
      {spacer()}
      {h2("Product and Segment View")}
      {summary_product}
      {spacer()}
      {h2("Geography and Competitive Outlook")}
      {summary_geo}
      {spacer()}

      // ── Analyst Opinion ───────────────────────────────────────────────
      {h1("Analyst Opinion")}
      {para(escape(n["analyst_name"]) + ", " + escape(n["analyst_title"]) + " says, '" + escape(c["analyst_quote"]) + "'")}
      {spacer()}

      // ── Definition ────────────────────────────────────────────────────
      {h2(escape(n["market_name"]) + " Definition")}
      {para(escape(c["definition"]))}
      {spacer()}

      {h2(escape(n["market_name"]) + " Inclusions")}
      {inclusions}
      {spacer()}

      {h2(escape(n["market_name"]) + " Exclusions")}
      {exclusions}
      {spacer()}

      {h2(escape(n["market_name"]) + " Research Methodology")}
      {para(escape(c["methodology"]))}
      {spacer()}

      // ── Drivers, Restraints, Trends ───────────────────────────────────
      {h2("Key Drivers, Restraints, and Trends in " + escape(n["market_name"]))}
      {h2("Drivers")}
      {para(escape(c["drivers_paragraph"]))}
      {spacer()}
      {h2("Restraints")}
      {para(escape(c["restraints_paragraph"]))}
      {spacer()}
      {h2("Trends")}
      {para(escape(c["trends_paragraph"]))}
      {spacer()}

      // ── Segmental Analysis ────────────────────────────────────────────
      {h1("Segmental Analysis")}
      {h2(escape(n["market_name"]) + " Analysis by " + escape(seg1["name"]))}
      {para(escape(c["segment1_analysis"]))}
      {spacer()}
      {h2(escape(n["market_name"]) + " Analysis by " + escape(seg2["name"]))}
      {para(escape(c["segment2_analysis"]))}
      {spacer()}
      {h2(escape(n["market_name"]) + " Analysis by " + escape(seg3["name"]))}
      {para(escape(c["segment3_analysis"]))}
      {spacer()}

      // ── Competitive Aligners ──────────────────────────────────────────
      {h2("Competitive Aligners for Market Players")}
      {para(escape(c["competitive_para1"]))}
      {spacer()}
      {para(escape(c["competitive_para2"]))}
      {spacer()}

      // ── Key Players ───────────────────────────────────────────────────
      {h2("Key Players in " + escape(n["market_name"]))}
      {key_players}
      {spacer()}

      // ── Strategic Outlook ─────────────────────────────────────────────
      {h2("Strategic Outlook by FMI on " + escape(n["market_name"]))}
      {para(escape(c["strategic_outlook"]))}
      {spacer()}

      // ── Scope Table ───────────────────────────────────────────────────
      {h1("Scope of the Report")}
      new Table({{
        width: {{ size: 9360, type: WidthType.DXA }},
        columnWidths: [3120, 6240],
        rows: [
          {scope_rows_js}
        ]
      }}),
      {spacer()}

      // ── Bibliography ──────────────────────────────────────────────────
      {h1("Bibliography")}
      {bib_items}
      {spacer()}

      // ── FAQs ──────────────────────────────────────────────────────────
      {h1("FAQs")}
      {faq_items}
    ]
  }}]
}});

Packer.toBuffer(doc).then(buffer => {{
  fs.writeFileSync('{output_path}', buffer);
  console.log('SUCCESS');
}}).catch(err => {{
  console.error('ERROR:', err.message);
  process.exit(1);
}});
"""
    return js_code


# ── Main run logic ───────────────────────────────────────────────────────────
if run_btn and api_key and title:
    client = openai.OpenAI(api_key=api_key)
    status_area = st.container()

    with status_area:
        st.markdown("---")

        # Step 1
        st.markdown('<div class="status-box">⚙️ <b>Step 1/3</b> — Generating market data and numbers...</div>', unsafe_allow_html=True)
        try:
            numbers = step1_generate_numbers(client, title)
            st.markdown(f'<div class="done-box">✅ Market data ready: USD {numbers["base_year_value_usd_bn"]}B base, CAGR {numbers["cagr_pct"]}%</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="error-box">❌ Step 1 failed: {str(e)}</div>', unsafe_allow_html=True)
            st.stop()

        # Step 2
        st.markdown('<div class="status-box">✍️ <b>Step 2/3</b> — Writing all report sections...</div>', unsafe_allow_html=True)
        try:
            content = step2_generate_content(client, title, numbers)
            st.markdown('<div class="done-box">✅ All sections written</div>', unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="error-box">❌ Step 2 failed: {str(e)}</div>', unsafe_allow_html=True)
            st.stop()

        # Step 3: Build docx
        st.markdown('<div class="status-box">📄 <b>Step 3/3</b> — Building Word document...</div>', unsafe_allow_html=True)
        try:
            safe_title = "".join(c for c in title[:50] if c.isalnum() or c in " _-").strip().replace(" ", "_")
            output_path = f"/tmp/{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            js_path = f"/tmp/gen_report_{int(time.time())}.js"

            # Install docx package into /tmp if not already there
            node_modules_path = "/tmp/node_modules"
            if not os.path.exists(os.path.join(node_modules_path, "docx")):
                install_result = subprocess.run(
                    ["npm", "install", "--prefix", "/tmp", "docx"],
                    capture_output=True, text=True, timeout=120
                )
                if install_result.returncode != 0:
                    raise Exception(f"npm install failed: {install_result.stderr}")

            js_code = build_docx(numbers, content, output_path)
            with open(js_path, "w") as f:
                f.write(js_code)

            env = os.environ.copy()
            env["NODE_PATH"] = node_modules_path

            result = subprocess.run(
                ["node", js_path],
                capture_output=True, text=True, timeout=60,
                env=env
            )

            if result.returncode != 0 or not os.path.exists(output_path):
                raise Exception(result.stderr or result.stdout or "Node.js generation failed")

            st.markdown('<div class="done-box">✅ Word document created</div>', unsafe_allow_html=True)

            # Download button
            st.markdown("---")
            with open(output_path, "rb") as f:
                docx_bytes = f.read()

            filename = f"{safe_title}_Market_Report.docx"
            st.download_button(
                label="⬇️ Download Report (.docx)",
                data=docx_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary"
            )
            st.success(f"Report ready: **{numbers['market_name']}** | {numbers['forecast_start']}-{numbers['forecast_end']} | CAGR {numbers['cagr_pct']}%")

            # Cleanup
            os.unlink(js_path)

        except Exception as e:
            st.markdown(f'<div class="error-box">❌ Step 3 failed: {str(e)}</div>', unsafe_allow_html=True)
            st.stop()
