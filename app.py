import streamlit as st
import openai
import json
import subprocess
import os
import time
import zipfile
import io
from datetime import datetime

st.set_page_config(page_title="Market Report Generator", page_icon="📊", layout="centered")

st.markdown("""
<style>
    .stApp { max-width: 820px; margin: 0 auto; }
    .status-box { background: #f0f4ff; border-left: 4px solid #4a6cf7; padding: 12px 16px; border-radius: 4px; margin: 6px 0; font-size: 14px; }
    .done-box { background: #f0fff4; border-left: 4px solid #38a169; padding: 12px 16px; border-radius: 4px; margin: 6px 0; font-size: 14px; }
    .error-box { background: #fff0f0; border-left: 4px solid #e53e3e; padding: 12px 16px; border-radius: 4px; margin: 6px 0; font-size: 14px; }
    .hint { font-size: 12px; color: #666; margin-top: 4px; }
    h1 { font-size: 1.8rem !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    st.markdown('<p class="hint">Never stored. Lives only in this session.</p>', unsafe_allow_html=True)
    st.divider()
    delay = st.slider("Pause between reports (seconds)", min_value=5, max_value=30, value=10, step=5)
    st.markdown('<p class="hint">Breathing room between API calls.</p>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**Report sections:**")
    st.markdown("Intro · Summary · Analyst Opinion · Definition · Inclusions/Exclusions · Methodology · Drivers/Restraints/Trends · Segmental Analysis · Competitive Outlook · Key Players · Strategic Outlook · Scope Table · Bibliography · FAQs")

st.title("📊 Market Report Generator")
st.markdown("Paste one title per line. Reports are processed one by one. You get a ZIP with all files at the end.")

titles_input = st.text_area("Market Titles (one per line)", placeholder="Global EV Battery Market\nFlower Pouches Market\nSmart Packaging Market", height=180)

raw_titles = [t.strip() for t in titles_input.strip().splitlines() if t.strip()]
n_titles = len(raw_titles)

if raw_titles:
    st.markdown(f"**{n_titles} title{'s' if n_titles > 1 else ''} queued:**")
    for i, t in enumerate(raw_titles):
        st.markdown(f"&nbsp;&nbsp;📋 **{i+1}.** {t}")

run_btn = st.button(
    f"Generate {n_titles} Report{'s' if n_titles > 1 else ''}" if raw_titles else "Generate Reports",
    type="primary",
    disabled=(not api_key or not raw_titles)
)

def call_gpt(client, system_prompt, user_prompt):
    response = client.chat.completions.create(
        model="gpt-5.4",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.4,
        max_completion_tokens=4096,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

SYSTEM_ANALYST = "You are a senior market research analyst. Generate realistic, internally consistent market data. base_year_value * (1 + cagr/100)^10 must approximately equal forecast_2036_value. Respond ONLY in valid JSON."
SYSTEM_WRITER = "You are a professional market research writer. Formal, analytical, third-person. Complete paragraphs. Respond ONLY in valid JSON."

def generate_numbers(client, title):
    return call_gpt(client, SYSTEM_ANALYST, f"""Generate realistic market data for: "{title}"
Return JSON:
{{
  "market_name": "Full market name",
  "base_year_value_usd_bn": 0.0,
  "forecast_2026_value_usd_bn": 0.0,
  "forecast_2036_value_usd_bn": 0.0,
  "cagr_pct": 0.0,
  "base_year": 2025,
  "forecast_start": 2026,
  "forecast_end": 2036,
  "segments": {{
    "axis1": {{"name": "e.g. Product Type", "segments": ["A","B","C"], "leader": "A", "leader_share_pct": 0.0}},
    "axis2": {{"name": "e.g. End Use Industry", "segments": ["X","Y"], "leader": "X", "leader_share_pct": 0.0}},
    "axis3": {{"name": "e.g. Region or Material", "segments": ["P","Q"], "leader": "P", "leader_share_pct": 0.0}}
  }},
  "regions": ["North America","Latin America","Western Europe","Eastern Europe","East Asia","South Asia and Pacific","Middle East and Africa"],
  "key_companies": ["Co1","Co2","Co3","Co4","Co5","Co6","Co7","Co8","Co9","Co10"],
  "analyst_name": "Full Name",
  "analyst_title": "Senior Consultant at FMI"
}}""")

def generate_content(client, title, n):
    seg1, seg2, seg3 = n["segments"]["axis1"], n["segments"]["axis2"], n["segments"]["axis3"]
    return call_gpt(client, SYSTEM_WRITER, f"""Write all content for a market research report on: "{title}"
Figures to use exactly: USD {n['base_year_value_usd_bn']}B ({n['base_year']}), USD {n['forecast_2036_value_usd_bn']}B (2036), CAGR {n['cagr_pct']}%, {seg1['leader']} {seg1['leader_share_pct']}% share, {seg2['leader']} {seg2['leader_share_pct']}% share, companies: {', '.join(n['key_companies'][:7])}, analyst: {n['analyst_name']}.
Return JSON:
{{
  "intro_paragraph": "2-sentence overview with all key numbers",
  "summary_snapshot_bullets": ["b1","b2","b3"],
  "summary_demand_bullets": ["b1","b2","b3"],
  "summary_product_bullets": ["b1","b2","b3"],
  "summary_geo_bullets": ["b1","b2","b3"],
  "analyst_quote": "One sharp sentence",
  "definition": "2-3 sentence definition",
  "inclusions": ["i1","i2","i3"],
  "exclusions": ["e1","e2","e3"],
  "methodology": "2-3 sentence methodology",
  "drivers_paragraph": "3-4 sentence drivers",
  "restraints_paragraph": "3-4 sentence restraints",
  "trends_paragraph": "3-4 sentence trends",
  "segment1_analysis": "3-4 sentences on {seg1['leader']} in {seg1['name']}",
  "segment2_analysis": "3-4 sentences on {seg2['leader']} in {seg2['name']}",
  "segment3_analysis": "3-4 sentences on {seg3['leader']} in {seg3['name']}",
  "competitive_para1": "4-5 sentences naming 2-3 companies with strategies",
  "competitive_para2": "4-5 sentences naming 2-3 more companies",
  "strategic_outlook": "3-4 sentence FMI strategic view",
  "bibliography": [{{"org":"Org","year":"2024","title":"Title"}},{{"org":"Org","year":"2025","title":"Title"}},{{"org":"Org","year":"2024","title":"Title"}},{{"org":"Org","year":"2023","title":"Title"}},{{"org":"Org","year":"2024","title":"Title"}},{{"org":"Org","year":"2025","title":"Title"}},{{"org":"Org","year":"2024","title":"Title"}}],
  "faqs": [{{"q":"How big is the {title.lower()}?","a":"Answer."}},{{"q":"What is the CAGR?","a":"Answer."}},{{"q":"Which {seg1['name'].lower()} leads?","a":"Answer."}},{{"q":"Which {seg2['name'].lower()} leads?","a":"Answer."}},{{"q":"What drives growth?","a":"Answer."}},{{"q":"Who are the key companies?","a":"Answer."}}]
}}""")

def build_docx(n, c, output_path):
    seg1, seg2, seg3 = n["segments"]["axis1"], n["segments"]["axis2"], n["segments"]["axis3"]
    def esc(s): return str(s).replace("\\","\\\\").replace("`","\\`").replace("${","\\${").replace('"',"'").replace("\n"," ")
    def h1(t): return f'new Paragraph({{heading:HeadingLevel.HEADING_1,children:[new TextRun({{text:"{esc(t)}",font:"Arial",size:32,bold:true}})]}}),\n'
    def h2(t): return f'new Paragraph({{heading:HeadingLevel.HEADING_2,children:[new TextRun({{text:"{esc(t)}",font:"Arial",size:26,bold:true}})]}}),\n'
    def para(t): return f'new Paragraph({{children:[new TextRun({{text:"{esc(t)}",font:"Arial",size:22}})]}}),\n'
    def sp(): return 'new Paragraph({children:[new TextRun("")]}),\n'
    def buls(items, ref): return "".join([f'new Paragraph({{numbering:{{reference:"{ref}",level:0}},children:[new TextRun({{text:"{esc(i)}",font:"Arial",size:22}})]}}),\n' for i in items])
    bibs = "".join([f'new Paragraph({{children:[new TextRun({{text:" {esc(b["org"])}. {esc(b["year"])}. ",font:"Arial",size:20}}),new TextRun({{text:"{esc(b["title"])}.",italics:true,font:"Arial",size:20}})]}}),\n' for b in c["bibliography"]])
    faqs = "".join([f'new Paragraph({{children:[new TextRun({{text:"{esc(f["q"])}",bold:true,font:"Arial",size:22}})]}}),\nnew Paragraph({{children:[new TextRun({{text:"{esc(f["a"])}",font:"Arial",size:22}})]}}),\n{sp()}' for f in c["faqs"]])
    scope_data = [("Metric","Value",True),("Market Value",f"USD {n['base_year_value_usd_bn']}B in {n['base_year']} to USD {n['forecast_2036_value_usd_bn']}B by {n['forecast_end']}",False),("CAGR",f"{n['cagr_pct']}% from {n['forecast_start']} to {n['forecast_end']}",False),("Base Year",str(n["base_year"]),False),("Forecast Period",f"{n['forecast_start']} to {n['forecast_end']}",False),(seg1["name"]+" Segmentation",", ".join(seg1["segments"]),False),(seg2["name"]+" Segmentation",", ".join(seg2["segments"]),False),(seg3["name"]+" Segmentation",", ".join(seg3["segments"]),False),("Regions Covered",", ".join(n["regions"]),False)]
    def srow(l,v,hdr): bg="E8F0FE" if hdr else "FFFFFF"; bd="true" if hdr else "false"; return f'new TableRow({{children:[new TableCell({{borders:{{top:cb,bottom:cb,left:cb,right:cb}},width:{{size:3120,type:WidthType.DXA}},shading:{{fill:"{bg}",type:ShadingType.CLEAR}},margins:{{top:80,bottom:80,left:120,right:120}},children:[new Paragraph({{children:[new TextRun({{text:"{esc(l)}",bold:{bd},font:"Arial",size:20}})]}})]}}),new TableCell({{borders:{{top:cb,bottom:cb,left:cb,right:cb}},width:{{size:6240,type:WidthType.DXA}},shading:{{fill:"{bg}",type:ShadingType.CLEAR}},margins:{{top:80,bottom:80,left:120,right:120}},children:[new Paragraph({{children:[new TextRun({{text:"{esc(v)}",font:"Arial",size:20}})]}})]}})]}})'
    scope_rows = ",\n".join([srow(l,v,h) for l,v,h in scope_data])
    brefs = ",".join([f'{{reference:"b{i}",levels:[{{level:0,format:LevelFormat.BULLET,text:"•",alignment:AlignmentType.LEFT,style:{{paragraph:{{indent:{{left:720,hanging:360}}}}}}}}]}}' for i in range(1,9)])
    children = (
        para(c["intro_paragraph"]) + sp() +
        h1("Report Summary") + h2("Market Snapshot") + buls(c["summary_snapshot_bullets"],"b1") + sp() +
        h2("Demand and Growth Drivers") + buls(c["summary_demand_bullets"],"b2") + sp() +
        h2("Product and Segment View") + buls(c["summary_product_bullets"],"b3") + sp() +
        h2("Geography and Competitive Outlook") + buls(c["summary_geo_bullets"],"b4") + sp() +
        h1("Analyst Opinion") + para(f'{esc(n["analyst_name"])}, {esc(n["analyst_title"])} says, \'{esc(c["analyst_quote"])}\'') + sp() +
        h2(esc(n["market_name"])+" Definition") + para(c["definition"]) + sp() +
        h2(esc(n["market_name"])+" Inclusions") + buls(c["inclusions"],"b5") + sp() +
        h2(esc(n["market_name"])+" Exclusions") + buls(c["exclusions"],"b6") + sp() +
        h2(esc(n["market_name"])+" Research Methodology") + para(c["methodology"]) + sp() +
        h2("Key Drivers, Restraints, and Trends in "+esc(n["market_name"])) +
        h2("Drivers") + para(c["drivers_paragraph"]) + sp() +
        h2("Restraints") + para(c["restraints_paragraph"]) + sp() +
        h2("Trends") + para(c["trends_paragraph"]) + sp() +
        h1("Segmental Analysis") +
        h2(esc(n["market_name"])+" Analysis by "+esc(seg1["name"])) + para(c["segment1_analysis"]) + sp() +
        h2(esc(n["market_name"])+" Analysis by "+esc(seg2["name"])) + para(c["segment2_analysis"]) + sp() +
        h2(esc(n["market_name"])+" Analysis by "+esc(seg3["name"])) + para(c["segment3_analysis"]) + sp() +
        h2("Competitive Aligners for Market Players") + para(c["competitive_para1"]) + sp() + para(c["competitive_para2"]) + sp() +
        h2("Key Players in "+esc(n["market_name"])) + buls(n["key_companies"],"b7") + sp() +
        h2("Strategic Outlook by FMI on "+esc(n["market_name"])) + para(c["strategic_outlook"]) + sp() +
        h1("Scope of the Report") +
        f'new Table({{width:{{size:9360,type:WidthType.DXA}},columnWidths:[3120,6240],rows:[{scope_rows}]}}),\n' + sp() +
        h1("Bibliography") + bibs + sp() +
        h1("FAQs") + faqs
    )
    return f"""const {{Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,HeadingLevel,AlignmentType,LevelFormat,BorderStyle,WidthType,ShadingType}}=require('docx');
const fs=require('fs');
const cb={{style:BorderStyle.SINGLE,size:1,color:"CCCCCC"}};
const doc=new Document({{
  numbering:{{config:[{brefs}]}},
  styles:{{default:{{document:{{run:{{font:"Arial",size:22}}}}}},paragraphStyles:[
    {{id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,run:{{size:32,bold:true,font:"Arial",color:"1F3864"}},paragraph:{{spacing:{{before:320,after:160}},outlineLevel:0}}}},
    {{id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,run:{{size:26,bold:true,font:"Arial",color:"2E5096"}},paragraph:{{spacing:{{before:240,after:120}},outlineLevel:1}}}}
  ]}},
  sections:[{{properties:{{page:{{size:{{width:12240,height:15840}},margin:{{top:1440,right:1440,bottom:1440,left:1440}}}}}},children:[
    {children}
  ]}}]
}});
Packer.toBuffer(doc).then(b=>{{fs.writeFileSync('{output_path}',b);console.log('OK');}}).catch(e=>{{console.error(e.message);process.exit(1);}});
"""

def ensure_docx_installed():
    if not os.path.exists("/tmp/node_modules/docx"):
        r = subprocess.run(["npm","install","--prefix","/tmp","docx"], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise Exception(f"npm install failed: {r.stderr}")

def run_node(js_code):
    js_path = f"/tmp/gen_{int(time.time()*1000)}.js"
    with open(js_path,"w") as f: f.write(js_code)
    env = os.environ.copy()
    env["NODE_PATH"] = "/tmp/node_modules"
    r = subprocess.run(["node", js_path], capture_output=True, text=True, timeout=60, env=env)
    try: os.unlink(js_path)
    except: pass
    if r.returncode != 0:
        raise Exception(r.stderr or r.stdout or "Node.js failed")

if run_btn and api_key and raw_titles:
    client = openai.OpenAI(api_key=api_key)
    st.markdown("---")

    with st.spinner("Setting up dependencies..."):
        try:
            ensure_docx_installed()
        except Exception as e:
            st.error(f"Setup failed: {e}")
            st.stop()

    completed_files = {}
    failed_titles = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, title in enumerate(raw_titles):
        status_text.markdown(f"**Processing {idx+1}/{n_titles}: {title}**")
        with st.container():
            st.markdown(f"#### {idx+1}. {title}")
            s1, s2, s3 = st.empty(), st.empty(), st.empty()

        try:
            s1.markdown('<div class="status-box">⚙️ Generating market data...</div>', unsafe_allow_html=True)
            numbers = generate_numbers(client, title)
            s1.markdown(f'<div class="done-box">✅ Data: USD {numbers["base_year_value_usd_bn"]}B base, CAGR {numbers["cagr_pct"]}%</div>', unsafe_allow_html=True)

            s2.markdown('<div class="status-box">✍️ Writing all sections...</div>', unsafe_allow_html=True)
            content = generate_content(client, title, numbers)
            s2.markdown('<div class="done-box">✅ All sections written</div>', unsafe_allow_html=True)

            s3.markdown('<div class="status-box">📄 Building Word document...</div>', unsafe_allow_html=True)
            safe_title = "".join(ch for ch in title[:50] if ch.isalnum() or ch in " _-").strip().replace(" ","_")
            output_path = f"/tmp/{safe_title}_{idx}.docx"
            run_node(build_docx(numbers, content, output_path))

            with open(output_path,"rb") as f: completed_files[f"{safe_title}.docx"] = f.read()
            try: os.unlink(output_path)
            except: pass
            s3.markdown('<div class="done-box">✅ Report complete</div>', unsafe_allow_html=True)

        except Exception as e:
            s3.markdown(f'<div class="error-box">❌ Failed: {str(e)[:200]}</div>', unsafe_allow_html=True)
            failed_titles.append(title)

        progress_bar.progress((idx+1)/n_titles)
        if idx < n_titles - 1:
            status_text.markdown(f"**Pausing {delay}s before next report...**")
            time.sleep(delay)

    st.markdown("---")
    status_text.markdown(f"**Done. {len(completed_files)}/{n_titles} reports generated.**")

    if completed_files:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, data in completed_files.items():
                zf.writestr(filename, data)
        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label=f"⬇️ Download All {len(completed_files)} Reports (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"Market_Reports_{timestamp}.zip",
            mime="application/zip",
            type="primary"
        )

    if failed_titles:
        st.warning("Failed: " + ", ".join(failed_titles))
