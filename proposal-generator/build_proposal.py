"""Consulting-style proposal generator (portrait A4 PDF).

Builds a 12-page, BCG/EY-style proposal from Python data: executive summary,
project landscape, feasibility scorecard, prioritisation matrix, revenue scenarios,
roadmap (Gantt), quick wins, risk heat map, risk register with Plan B, and sources.
Charts and diagrams are drawn as inline SVG/HTML and printed to PDF with headless Chromium.

Usage:
    pip install playwright && playwright install chromium
    python build_proposal.py
"""
import os
os.makedirs("output", exist_ok=True)
from playwright.sync_api import sync_playwright

NAVY, TEAL, GOLD, GREY, LIGHT = "#0B2545", "#13A89E", "#E0A458", "#5B6B7A", "#EEF3F7"
TOTAL = 18

def page(n, section, title, body, sub=""):
    return f"""
<section class="page">
  <div class="top"><span class="sec">{section}</span><span class="track">6-Month Plan &middot; LLM Corporation Sdn. Bhd.</span></div>
  <h1>{title}</h1>
  {f'<p class="sub">{sub}</p>' if sub else ''}
  <div class="body">{body}</div>
  <div class="foot"><span>Prepared by Ahmad Muazamil bin Ishak &middot; Candidate, Eksekutif Operasi</span><span>__PG__</span></div>
</section>"""

# ---------- reusable visuals ----------
def chevrons(items):
    out = '<div class="chev">'
    for i, (when, name, desc, col) in enumerate(items):
        out += f'<div class="cv" style="background:{col}"><div class="cvw">{when}</div><div class="cvn">{name}</div><div class="cvd">{desc}</div></div>'
    return out + "</div>"

def kpi_tiles(tiles):
    return '<div class="tiles">' + "".join(
        f'<div class="tile"><div class="big">{v}</div><div class="lab">{l}</div></div>' for v, l in tiles) + "</div>"

OPPS = [  # name, short, revenue, speed, approval-ease, mandate fit, risk(low=5)
    ("Telco towers &amp; fibre on highway reserves", "Telco & fibre", 4, 4, 3, 5, 4),
    ("Roadside advertising", "Advertising", 3, 5, 3, 4, 5),
    ("Project management &amp; engineering services", "PM services", 3, 3, 4, 5, 4),
    ("Training &amp; highway-safety events", "Training", 1, 4, 5, 4, 5),
    ("EV charging at rest areas &amp; lay-bys", "EV charging", 3, 2, 2, 4, 4),
    ("Solar on unused highway land", "Solar", 5, 1, 2, 3, 3),
    ("Space &amp; shops at R&amp;R (via concessionaires)", "R&R space", 3, 2, 2, 3, 3),
    ("Traffic &amp; highway data services", "Data", 2, 2, 2, 4, 3),
]
W = (0.30, 0.25, 0.20, 0.15, 0.10)
def score(o): return sum(w * s for w, s in zip(W, o[2:]))
def ease(o): return (o[3] + o[4] + o[6]) / 3

def matrix_svg():
    w, h, pad, top, right = 640, 520, 62, 16, 16
    lo, hi, th = 0.5, 5.5, 2.75
    X = lambda v: pad + (v - lo) / (hi - lo) * (w - pad - right)
    Y = lambda v: h - pad - (v - lo) / (hi - lo) * (h - pad - top)
    mx, my = X(th), Y(th)
    s = f'<svg viewBox="0 0 {w} {h}" class="svg">'
    R, B = w - right, h - pad
    quads = [(mx, top, R - mx, my - top, "#DDF3F0"), (pad, top, mx - pad, my - top, "#FBEFDD"),
             (mx, my, R - mx, B - my, "#EEF3F7"), (pad, my, mx - pad, B - my, "#F4F4F4")]
    for x, y, ww, hh, f in quads:
        s += f'<rect x="{x}" y="{y}" width="{ww}" height="{hh}" fill="{f}"/>'
    for x, y, t, c, a in [(R - 10, top + 22, "QUICK WINS", "#0E7C74", "end"), (pad + 10, top + 22, "STRATEGIC BETS", "#A86A1C", "start"),
                          (R - 10, B - 12, "FILL-INS", GREY, "end"), (pad + 10, B - 12, "DEPRIORITISE", "#8A8A8A", "start")]:
        s += f'<text x="{x}" y="{y}" font-size="13" font-weight="800" fill="{c}" letter-spacing="1.2" text-anchor="{a}">{t}</text>'
    s += f'<line x1="{pad}" y1="{B}" x2="{R}" y2="{B}" stroke="{NAVY}" stroke-width="1.5"/>'
    s += f'<line x1="{pad}" y1="{top}" x2="{pad}" y2="{B}" stroke="{NAVY}" stroke-width="1.5"/>'
    s += f'<text x="{(pad+R)/2}" y="{h-16}" font-size="14" text-anchor="middle" fill="{NAVY}" font-weight="600">Ease of implementation (speed, approvals, risk) &#8594;</text>'
    s += f'<text transform="translate(20,{(B+top)/2}) rotate(-90)" font-size="14" text-anchor="middle" fill="{NAVY}" font-weight="600">Revenue potential &#8594;</text>'
    for v in (1, 2, 3, 4, 5):
        s += f'<text x="{X(v)}" y="{B+18}" font-size="11" text-anchor="middle" fill="{GREY}">{v}</text>'
        s += f'<text x="{pad-10}" y="{Y(v)+4}" font-size="11" text-anchor="end" fill="{GREY}">{v}</text>'
    below = {"PM services", "EV charging"}
    for o in OPPS:
        x, y = X(ease(o)), Y(o[2])
        r = 8 + score(o) * 3.2
        col = TEAL if ease(o) >= th and o[2] >= th else (GOLD if o[2] >= th else GREY)
        s += f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}" fill-opacity="0.88" stroke="white" stroke-width="2"/>'
        ly = y + r + 15 if o[1] in below else y - r - 7
        s += f'<text x="{x}" y="{ly}" font-size="13" font-weight="700" text-anchor="middle" fill="{NAVY}">{o[1].replace("&", "&amp;")}</text>'
    return s + "</svg>"

def gantt():
    months = ["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"]
    rows = [
        ("Operations", [(0, 1, "Take over", NAVY), (1, 6, "Weekly status rhythm", "#3E5C76")], [(1, "Tracker live")]),
        ("Contracts &amp; compliance", [(0, 2, "Contract register &amp; terms review", NAVY), (2, 6, "Monthly vendor reviews &amp; site inspections", "#3E5C76")], [(2, "Register complete")]),
        ("Business development", [(0, 1, "Idea list", TEAL), (1, 3, "Screen &amp; market sounding", TEAL), (3, 6, "Proposals &#8594; MOU / tender", "#0E7C74")], [(3, "Shortlist tested"), (5, "Proposals ready")]),
        ("Stakeholders", [(0, 2, "Map &amp; meet stakeholders", GOLD), (2, 6, "Regular check-ins &amp; partner site visits", "#C98A3E")], []),
        ("Digital &amp; AI", [(1, 3, "Automate reports &amp; alerts", "#7A8FA3"), (3, 6, "Pipeline dashboard", "#7A8FA3")], [(3, "Auto-report live")]),
    ]
    head = "".join(f'<div class="gm">{m}</div>' for m in months)
    out = f'<div class="gantt"><div class="gl"></div>{head}'
    for name, bars, ms in rows:
        out += f'<div class="gl">{name}</div><div class="gr">'
        for a, b, t, c in bars:
            out += f'<div class="gb" style="left:{a/6*100}%;width:calc({(b-a)/6*100}% - 4px);background:{c}">{t}</div>'
        for m, t in ms:
            out += f'<div class="gd" style="left:calc({m/6*100}% - 7px)" title="{t}"></div><div class="gdt" style="left:calc({m/6*100}% - 50px)">{t}</div>'
        out += "</div>"
    return out + "</div>"

def funnel():
    st = [("Ideas", "from permits, sites, colleagues", 100), ("Screened", "scored on 5 criteria", 86), ("Concept note", "agreed with manager", 72),
          ("Market sounding", "tested with partners", 58), ("Proposal", "legal &amp; finance reviewed", 46), ("Agreement", "MOU / LOI / tender", 34)]
    cols = [NAVY, "#1D3D63", "#2E5A80", "#0E7C74", TEAL, GOLD]
    out = '<div class="funnel">'
    for (n, v, wdt), c in zip(st, cols):
        out += f'<div class="fs" style="width:{wdt}%;background:{c}"><span class="fv" style="font-size:15px">{n}</span><span class="fn">{v}</span></div>'
    return out + "</div>"

def horizons():
    hs = [("Horizon 1", "Months 0-6", "Monetise what already exists", ["Telco &amp; fibre rights of way", "Roadside advertising", "PM &amp; engineering services", "Operations discipline &amp; reporting"], TEAL),
          ("Horizon 2", "Months 6-18", "Scale partnerships", ["EV charging network with operators", "R&amp;R space with concessionaires", "Multi-year framework agreements", "Revenue targets per stream"], "#3E5C76"),
          ("Horizon 3", "Months 18-36", "Build new platforms", ["Solar on highway land (PPA / lease)", "Traffic data products", "Regional expansion of services", "Recurring revenue base"], GOLD)]
    out = '<div class="hz">'
    for i, (h, t, d, items, c) in enumerate(hs):
        li = "".join(f"<li>{x}</li>" for x in items)
        out += f'<div class="hc" style="border-top:6px solid {c};margin-top:{(2-i)*60}px"><div class="hh" style="color:{c}">{h}</div><div class="ht">{t}</div><div class="hd">{d}</div><ul>{li}</ul></div>'
    return out + "</div>"

# ---------- pages ----------
pages = []
pages.append(f"""
<section class="page cover">
  <div class="cband"></div>
  <div class="ctext">
    <div class="ckick">PROPOSAL &middot; NOVEMBER 2026</div>
    <div class="ctitle">Unlocking Commercial Value from Highway Assets</div>
    <div class="csub">A 6-month operations and business development plan for the role of Eksekutif Operasi, LLM Corporation Sdn. Bhd.</div>
    <div class="cline"></div>
    <div class="cby">Prepared by<br><b>Ahmad Muazamil bin Ishak</b><br>Assistant Manager, Malaysia Productivity Corporation<br>Candidate, Eksekutif Operasi</div>
  </div>
  <svg class="cart" viewBox="0 0 600 420">
    <path d="M-20 400 C 150 300, 250 330, 330 220 S 520 60, 640 40" stroke="#13A89E" stroke-width="46" fill="none" stroke-linecap="round" opacity="0.9"/>
    <path d="M-20 400 C 150 300, 250 330, 330 220 S 520 60, 640 40" stroke="white" stroke-width="3" stroke-dasharray="18 16" fill="none"/>
    <circle cx="330" cy="220" r="16" fill="#E0A458"/><circle cx="520" cy="95" r="12" fill="#E0A458"/><circle cx="150" cy="320" r="10" fill="#E0A458"/>
    <rect x="300" y="120" width="10" height="70" fill="#7A8FA3"/><path d="M305 110 l-18 22 h36z" fill="#7A8FA3"/>
    <rect x="420" y="170" width="70" height="40" rx="4" fill="#3E5C76"/><rect x="452" y="210" width="6" height="30" fill="#3E5C76"/>
  </svg>
  <div class="cnote">Based on the job advertisement and public information. All opportunities, scores and targets are indicative and to be validated with management.</div>
</section>""")

pages.append(page(2, "Executive summary",
  "In six months, the role can build a clear view of LLM Corporation's revenue opportunities while running operations with audit-grade discipline",
  kpi_tiles([("Learn", "the business, its assets, contracts and people"), ("Organise", "projects, contracts and reporting in one place"),
             ("Test", "the most promising revenue ideas with real partners"), ("Propose", "well-prepared business cases for management to decide")]) +
  """<div class="cols3">
   <div class="card"><div class="ct">1 &middot; Monetise what exists</div><p>The fastest revenue comes from assets and rights the group already controls: highway reserves, rights of way and in-house engineering know-how, not from new construction.</p></div>
   <div class="card"><div class="ct">2 &middot; Win trust through operations</div><p>A single project tracker, contract register and weekly report make every project visible. Clean delivery earns management's trust to take bigger deals forward.</p></div>
   <div class="card"><div class="ct">3 &middot; Stage-gate every deal</div><p>Each idea moves through screening, concept note, market sounding and proposal, with legal and finance checks, so approvals are fast and compliant.</p></div>
  </div>
  <div class="callout"><b>Recommendation:</b> prioritise three quick-win streams (telco and fibre rights of way, roadside advertising, project management services) in months 1 to 3, and open early talks on the new Central Spine Road and Kelantan R&amp;Rs, the MCMC tower programme and highway EV charging, then develop the strongest into formal proposals for management.</div>"""))

pages.append(page(3, "Context",
  "LLM Corporation's role is to earn revenue for the Highway Authority group, within the limits of concessions, approvals and public procurement",
  """<div class="cols2">
   <div><div class="h2">What we know</div><ul class="ul">
     <li>LLM Corporation Sdn. Bhd. is a wholly owned subsidiary of Lembaga Lebuhraya Malaysia (LLM), a federal statutory body under the Ministry of Works.</li>
     <li>The role is responsible for business opportunities and revenue strategy, daily operations, project delivery, contract and vendor monitoring, site visits and compliance.</li>
     <li>The role asks for AI skills (Microsoft Azure, Google Cloud) and strong Microsoft Office reporting.</li></ul></div>
   <div><div class="h2">What we assume (to validate)</div><ul class="ul">
     <li>The company commercialises highway-related land, rights and expertise.</li>
     <li>Most tolled highways and rest areas are run by concessionaires, so many deals need their agreement.</li>
     <li>Larger deals need management or board approval and may require tenders.</li>
     <li>The team is small, so one executive covers operations and business development.</li></ul></div>
  </div>
  <div class="h2" style="margin-top:22px">Who shapes every deal</div>
  <div class="stake">
   <div class="sk core">LLM Corporation<br><small>Operations Executive</small></div>
   <div class="sk s1">Lembaga Lebuhraya Malaysia<br><small>approvals, assets, divisions</small></div>
   <div class="sk s2">Highway concessionaires<br><small>R&amp;R, land access, operations</small></div>
   <div class="sk s3">Commercial partners<br><small>telcos, advertisers, EV, solar</small></div>
   <div class="sk s4">Vendors &amp; contractors<br><small>delivery, site works</small></div>
   <div class="sk s5">Regulators &amp; agencies<br><small>Ministry of Works, local councils</small></div>
  </div>"""))

pages.append(page(4, "Approach",
  "The plan runs in three phases: diagnose the business, organise and test, then propose and close",
  chevrons([("MONTH 1", "Diagnose", "Learn the business, take over every project and contract, map stakeholders, collect ideas", NAVY),
            ("MONTHS 2-3", "Organise &amp; test", "Weekly reporting rhythm, contract register, screen ideas, test the strongest ideas with partners", "#2E5A80"),
            ("MONTHS 4-6", "Propose &amp; close", "Full business cases, legal and finance review, management approval, MOU or tender", TEAL)]) +
  """<div class="cols3" style="margin-top:26px">
   <div class="card"><div class="ct">Phase 1 outputs</div><ul class="ul sm"><li>Project &amp; contract register</li><li>Stakeholder map</li><li>Long list of ideas</li><li>Day-30 note to manager</li></ul></div>
   <div class="card"><div class="ct">Phase 2 outputs</div><ul class="ul sm"><li>Weekly one-page status report</li><li>Contract calendar with alerts</li><li>Scored shortlist &amp; concept notes</li><li>Exploratory partner meetings</li></ul></div>
   <div class="card"><div class="ct">Phase 3 outputs</div><ul class="ul sm"><li>Business proposals for the strongest ideas</li><li>Next formal step agreed, where ready</li><li>Automated reporting</li><li>Month-6 review &amp; next-year plan</li></ul></div>
  </div>
  <div class="callout">Each phase ends with a gate review with my manager: what was delivered, what was learned, and whether to continue, change or stop each workstream.</div>"""))

rows = "".join(f"<tr><td><b>{o[0]}</b></td><td>{d}</td><td>{m}</td></tr>" for o, (d, m) in zip(OPPS, [
    ("Telcos, tower &amp; fibre companies", "Rental, right-of-way fees"),
    ("Outdoor advertising companies", "Space rental, revenue share"),
    ("Concessionaires, state agencies", "Service fees"),
    ("Contractors, agencies", "Course &amp; event fees"),
    ("EV charging operators", "Site rental, revenue share"),
    ("Solar developers, utilities", "Land lease, energy sale"),
    ("F&amp;B chains, retailers", "Tenancy via concessionaire"),
    ("Logistics firms, planners", "Data licence, reports")]))
pages.append(page(5, "Opportunity landscape",
  "Eight revenue streams are worth testing; most rely on assets and rights the group already controls",
  f"""<table class="tbl"><thead><tr><th>Opportunity</th><th>Who pays</th><th>Revenue model</th></tr></thead><tbody>{rows}</tbody></table>
  <div class="callout">Where ideas come from: permit requests LLM already receives, site visits, colleagues in LLM divisions, concessionaire meetings and industry news. Existing permit requests are the warmest leads and the first place to look.</div>"""))

srows = ""
for o in sorted(OPPS, key=score, reverse=True):
    cells = "".join(f'<td><span class="dot d{v}">{v}</span></td>' for v in o[2:])
    srows += f"<tr><td><b>{o[1].replace('&','&amp;')}</b></td>{cells}<td class='tot'>{score(o):.2f}</td></tr>"
pages.append(page(6, "Feasibility assessment",
  "A weighted scorecard ranks telco and fibre, advertising and project services highest on feasibility",
  f"""<p class="lead">Each opportunity is scored 1 (weak) to 5 (strong) on five criteria. For approvals and risk, a higher score means easier or safer.</p>
  <table class="tbl sc"><thead><tr><th>Opportunity</th><th>Revenue<br>potential<br><small>30%</small></th><th>Speed to<br>revenue<br><small>25%</small></th><th>Ease of<br>approval<br><small>20%</small></th><th>Mandate<br>fit<br><small>15%</small></th><th>Low risk &amp;<br>capex<br><small>10%</small></th><th>Weighted<br>score</th></tr></thead><tbody>{srows}</tbody></table>
  <p class="note">Scores are indicative, based on desk assumptions. They will be re-scored with real data and partner feedback in month 2.</p>"""))

pages.append(page(7, "Prioritisation",
  "Plotting value against ease separates quick wins to start now from strategic bets to prepare for next year",
  f"""<div class="mx">{matrix_svg()}</div>
  <div class="cols2" style="margin-top:14px">
   <div class="card"><div class="ct" style="color:#0E7C74">Quick wins: start in months 1-3</div><p>Telco &amp; fibre, roadside advertising and project management services: good revenue, fast to set up, few new approvals.</p></div>
   <div class="card"><div class="ct" style="color:#A86A1C">Strategic bets: prepare for year 2</div><p>Solar, EV charging and R&amp;R space: higher value or strategic, but need concessionaire agreement, capital or long approvals.</p></div>
  </div>
  <p class="note">Bubble size = weighted feasibility score. Training is a low-value fill-in for relationships; traffic data waits until data-sharing rules are clear.</p>"""))

pages.append(page(8, "Quick wins",
  "Ten quick wins in the first 90 days build credibility in operations and give the first commercial results",
  """<div class="cols2">
   <div><div class="h2 t">Operations quick wins</div>
    <div class="qw"><span>1</span><div><b>One project tracker</b><br>Every project with owner, deadline, budget and status</div></div>
    <div class="qw"><span>2</span><div><b>Contract register &amp; calendar</b><br>Payments, deliverables and renewals due in 60 days, with alerts</div></div>
    <div class="qw"><span>3</span><div><b>One-page weekly report</b><br>Progress, cost against budget, issues and next steps every Monday</div></div>
    <div class="qw"><span>4</span><div><b>Minutes within 24 hours</b><br>Every action with an owner and a due date</div></div>
    <div class="qw"><span>5</span><div><b>AI-assisted reporting</b><br>Automate the weekly report and contract alerts to free time for business development</div></div></div>
   <div><div class="h2 g">Commercial quick wins</div>
    <div class="qw c"><span>6</span><div><b>Review pending permit requests</b><br>Turn existing telco, fibre and utility requests into paid agreements</div></div>
    <div class="qw c"><span>7</span><div><b>Advertising site audit</b><br>List compliant roadside sites and current usage; size the opportunity</div></div>
    <div class="qw c"><span>8</span><div><b>Services offer sheet</b><br>One-page offer of project management and engineering services for agencies</div></div>
    <div class="qw c"><span>9</span><div><b>EV charging sounding</b><br>Meet charging operators to test interest in rest-area sites</div></div>
    <div class="qw c"><span>10</span><div><b>Partner site visits</b><br>Bring interested partners to see real locations and speed up decisions</div></div></div>
  </div>"""))

pages.append(page(9, "Roadmap",
  "The six-month roadmap runs five workstreams in parallel, with clear milestones at months 1, 3 and 5",
  gantt() + """<div class="legend"><span><i style="background:#0B2545"></i>Operations &amp; contracts</span><span><i style="background:#13A89E"></i>Business development</span><span><i style="background:#E0A458"></i>Stakeholders</span><span><i style="background:#7A8FA3"></i>Digital &amp; AI</span><span><i class="dia"></i>Milestone</span></div>
  <table class="tbl" style="margin-top:22px"><thead><tr><th style="width:12%">Gate</th><th style="width:22%">When</th><th>What must be true to pass</th></tr></thead><tbody>
  <tr><td><b>Gate 1</b></td><td>End of month 1</td><td>All projects and contracts in the tracker; first idea list shared; priorities agreed with manager</td></tr>
  <tr><td><b>Gate 2</b></td><td>End of month 3</td><td>Weekly report running; shortlisted opportunities tested with partners</td></tr>
  <tr><td><b>Gate 3</b></td><td>End of month 6</td><td>Proposals for the strongest opportunities with management; plan for the next year agreed</td></tr></tbody></table>"""))

pages.append(page(10, "Business development engine",
  "A stage-gated pipeline moves ideas step by step towards agreements, with legal, finance and management checks built in",
  f"""<div class="cols2 fun">{funnel()}<div>
   <div class="stg"><b>Screen</b> on revenue, speed, approvals, mandate fit and risk</div>
   <div class="stg"><b>Concept note</b>: one page on asset, partner type, revenue model and approvals, agreed with manager</div>
   <div class="stg"><b>Market sounding</b> with 10 to 20 target partners per stream, warm channels first</div>
   <div class="stg"><b>Proposal</b>: scope of work, cost estimate, 3 to 5-year revenue, risks; reviewed by legal and finance</div>
   <div class="stg"><b>Agreement</b>: management or board approval, then MOU, LOI, tender or contract</div></div></div>
  <div class="callout">How partners are reached, in order: (1) companies already applying to LLM for permits; (2) introductions through LLM divisions and concessionaires; (3) industry events and associations; (4) targeted LinkedIn outreach and formal letters to a short list. Mass cold emails are a last resort.</div>
  <p class="note">Each stage narrows the list: only ideas that pass a stage move to the next, so many ideas are needed for each agreement.</p>"""))

pages.append(page(11, "Operating model",
  "A fixed weekly rhythm and simple tools keep operations, contracts and relationships under control",
  """<table class="tbl"><thead><tr><th style="width:22%">When</th><th>What happens</th><th style="width:26%">Output</th></tr></thead><tbody>
   <tr><td><b>Monday</b></td><td>Update project tracker and pipeline</td><td>One-page status report to manager</td></tr>
   <tr><td><b>Tuesday-Thursday</b></td><td>Vendor, partner and LLM division meetings; site visits and inspections</td><td>Minutes within 24 hours; site reports with photos</td></tr>
   <tr><td><b>Thursday</b></td><td>Check contract calendar for the next 60 days</td><td>Alerts and follow-ups sent</td></tr>
   <tr><td><b>Friday</b></td><td>Close open actions, plan next week</td><td>Updated action log</td></tr>
   <tr><td><b>Monthly</b></td><td>Vendor performance reviews; pipeline review with management</td><td>Vendor scorecards; pipeline report</td></tr></tbody></table>
  <div class="cols3" style="margin-top:22px">
   <div class="card"><div class="ct">Coordinating operations</div><ul class="ul sm"><li>Every project has an owner, deadline and status</li><li>Problems raised early, with a proposed fix</li></ul></div>
   <div class="card"><div class="ct">Managing relationships</div><ul class="ul sm"><li>One named contact per partner and division</li><li>Contact log of promises and dates</li><li>Bad news to my manager first</li></ul></div>
   <div class="card"><div class="ct">Monitoring contracts</div><ul class="ul sm"><li>Monthly delivery check against terms</li><li>Written notice, deadline, then escalation for gaps</li><li>Safety and quality inspections</li></ul></div>
  </div>"""))

pages.append(page(12, "Long-term plan",
  "Beyond six months, the plan moves from monetising existing assets to scaling partnerships and building new platforms",
  horizons() + """<div class="callout" style="margin-top:24px">The first six months lay the base for horizons 2 and 3: the pipeline, the partner relationships and the trust of management. Strategic bets such as solar and EV charging are prepared during months 4 to 6 so they can start in year 2.</div>"""))

pages.append(page(13, "Next steps",
  "Four questions to confirm with management will turn this plan into an agreed work programme",
  f"""<div class="h2">Questions to confirm with management</div>
  <ol class="ul">
   <li>What are the company's current revenue sources and this year's revenue target?</li>
   <li>Which assets and rights can the company commercialise alone, and which need concessionaire or LLM approval?</li>
   <li>What are the agreed KPIs for this role, and is any pay linked to revenue?</li>
   <li>How much field work and travel does the role involve, and who does it report to?</li></ol>
  <div class="why"><b>Why me:</b> 4+ years in audit, risk and stakeholder work; seminars delivered for 9 government and corporate organisations; and daily use of AI to build reports, trackers and internal data platforms at Malaysia Productivity Corporation.</div>"""))


# ---------- NEW: research-based pages ----------
def src(t): return f'<p class="src">Sources: {t}</p>'

proj = [
 ("MCMC-LLM telco towers", "77 new towers along ~50 km of highway with poor coverage; MoU signed Jul 2026; LLM acts as facilitator", "Planned", "Site access, rights of way"),
 ("Central Spine Road (LTU) R&amp;R, Pahang", "Packages opened 12 Nov 2026; KKR has identified an R&amp;R site; who builds and runs it is still under discussion", "Planning", "R&amp;R operator, tenants, EV"),
 ("Kelantan R&amp;Rs: Laloh (LTU) and Bukit Bakar, Machang (KBKK)", "Two R&amp;Rs planned by the state; designs not finalised", "Planning", "Tenants, local SMEs, EV"),
 ("NPE extension (NPE2), Klang Valley", "RM1.7 bil project by IJM; about 6% progress; NPE carries 200,000+ vehicles a day", "Construction", "Advertising, utilities corridors"),
 ("Solar LED lighting", "RM25.2 mil for about 3,000 units at 32 high-risk locations (Budget 2026)", "Delivery", "Project monitoring, O&amp;M contracts"),
 ("Motorcycle shelters", "18 new locations targeted in 2026 on NSE, LDP, KESAS, LPT1 and others", "Delivery", "Sponsorship, advertising"),
 ("Smart highways &amp; traffic control centre", "Target of 50% of highways with smart technology; MLFF tolling under discussion", "Planning", "Data services, tech partners"),
 ("Highway EV charging", "Gentari and LLM opened an intercity EV hub at Petronas Penchala Link; PLUS targets 350 chargers by 2028", "Expanding", "Site rental, revenue share"),
]
pr = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td class='c'><span class='st'>{c}</span></td><td>{d}</td></tr>" for a,b,c,d in proj)
P_PROJECTS = page(0, "Current project landscape",
  "Eight live or planned highway projects create concrete commercial openings for LLM Corporation in the next 6 to 18 months",
  f"""<table class="tbl"><thead><tr><th style="width:24%">Project</th><th>What is happening</th><th class='c' style="width:13%">Status</th><th style="width:20%">Commercial opening</th></tr></thead><tbody>{pr}</tbody></table>
  <div class="callout"><b>Where to start:</b> the new R&amp;Rs on the Central Spine Road and in Kelantan, the MCMC tower programme and highway EV charging. Each has a decision still open, so LLM Corporation can shape the commercial model early.</div>
  {src("Bernama (30 Jul, 27 Jul, 23 Jun, 29 Sep, 19 Oct, 12 Nov 2026; 22 Jul 2025); Kosmo; Paultan; Focus Malaysia; Carz. Full links on the Sources page. Projects are run by LLM, KKR, JKR, state governments or concessionaires; LLM Corporation's exact role in each must be confirmed.")}""")

P_SPOT = page(0, "Spotlight: Central Spine Road R&amp;R",
  "The new Central Spine Road R&amp;R needs an operator; LLM Corporation could run it as a managed site with local tenants",
  """<div class="cols2">
   <div><div class="h2">The situation</div><ul class="ul">
    <li>KKR has identified an R&amp;R site on the Central Spine Road (LTU) in Pahang. Who builds and manages it is still being discussed with the state.</li>
    <li>In 2024, KKR sought about RM20 mil to build R&amp;R facilities on both sides of the road.</li>
    <li>Earlier, private investors did not come forward: traffic is low except during festive seasons.</li>
    <li>Kelantan also plans R&amp;Rs at Laloh (LTU) and Bukit Bakar, Machang (KBKK).</li></ul></div>
   <div><div class="h2">The proposal</div><ul class="ul">
    <li><b>Role:</b> LLM Corporation acts as site operator or managing agent for a publicly built R&amp;R, not as the investor.</li>
    <li><b>Tenants:</b> a convenience store and fuel station as anchors, local food stalls run by Pahang and Kelantan SMEs, and a prayer and rest area.</li>
    <li><b>Add-ons:</b> EV charging bays on a revenue share, sponsored signage, festive-season pop-up markets.</li>
    <li><b>Why it fits:</b> low weekday traffic suits small local tenants on flexible terms, not big investors.</li></ul></div>
  </div>
  <div class="h2" style="margin-top:22px">How it would be set up</div>
  <div class="chev sm4">
   <div class="cv" style="background:#0B2545"><div class="cvn">1 &middot; Confirm role</div><div class="cvd">With LLM, KKR and the state: operator, agent or advisor</div></div>
   <div class="cv" style="background:#2E5A80"><div class="cvn">2 &middot; Tenant mix</div><div class="cvd">Sound out anchors and local SME associations</div></div>
   <div class="cv" style="background:#0E7C74"><div class="cvn">3 &middot; Business case</div><div class="cvd">Rents, operating costs, festive-season peaks</div></div>
   <div class="cv" style="background:#13A89E"><div class="cvn">4 &middot; Tender</div><div class="cvd">Open, fair selection of tenants and partners</div></div>
  </div>
  """ + src("Bernama, 12 Nov 2026 and 22 Jul 2025; Carz, Oct 2024 (citing KKR). The operating model is a proposal for discussion."))

partners = [
 ("Convenience &amp; fuel anchors", "Petronas Dagangan, Shell Malaysia, BHPetrol, 7-Eleven Malaysia, KK Mart, myNEWS", "Anchor tenant at new R&amp;Rs"),
 ("Food &amp; beverage", "Marrybrown, Zus Coffee, Tealive and local Pahang and Kelantan food SMEs", "Food court and kiosk tenants"),
 ("EV charging", "Gentari, TNB Electron, ChargEV, JomCharge, Shell Recharge, DC Handal", "Charging bays at R&amp;Rs and lay-bys"),
 ("Telco &amp; towers", "CelcomDigi, Maxis, U Mobile, TM, edotco", "Tower sites and fibre on highway reserves"),
 ("Outdoor advertising", "Outdoor media owners such as Big Tree Outdoor", "Sponsored shelters, signage, R&amp;R screens"),
 ("Local partners", "State economic development corporations, district councils, SME associations", "Local tenants, permits, festive markets"),
]
pt = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>" for a,b,c in partners)
P_PARTNERS = page(0, "Target partners",
  "A focused long-list of about 25 partners covers every opening, starting with companies already active on highways",
  f"""<table class="tbl"><thead><tr><th style="width:22%">Segment</th><th>Who to approach</th><th style="width:28%">What we offer them</th></tr></thead><tbody>{pt}</tbody></table>
  <div class="cols3">
   <div class="card"><div class="ct">1 &middot; Warm first</div><p>Start with partners already working with LLM or concessionaires, such as Gentari on EV charging and telcos in the MCMC programme.</p></div>
   <div class="card"><div class="ct">2 &middot; Clear offer</div><p>A one-page offer per segment: the site, traffic, terms and the approval steps LLM Corporation will handle for them.</p></div>
   <div class="card"><div class="ct">3 &middot; Fair process</div><p>Interest from sounding meetings feeds an open tender or request for proposal, so selection stays transparent.</p></div>
  </div>
  <p class="note">Names are an approach list based on public activity, not confirmed interest. Partners are chosen through LLM's procurement rules.</p>""")

# revenue scenarios: (stream, low, base, high, assumption)
rev = [
 ("Telco tower site access", 0.46, 0.92, 1.39, "77 towers x RM500 / RM1,000 / RM1,500 a month, if access fees apply"),
 ("New R&amp;R as operator (per site)", 0.19, 0.44, 0.73, "16-24 stalls at RM600-1,200 + convenience anchor RM5-10k + fuel lease up to RM20k + EV bay rent, a month"),
 ("EV charging revenue share (5 sites)", 0.15, 0.30, 0.45, "20-60 sessions a day x 30 kWh x RM1.70, with an 8% revenue share"),
 ("Sponsorship &amp; advertising", 0.10, 0.20, 0.40, "Sponsored shelters, R&amp;R screens and signage, where safety rules allow"),
]
def rev_svg():
    w, h, lp, rp, top, rowh = 640, 320, 250, 90, 30, 58
    mx = 1.6
    X = lambda v: lp + v / mx * (w - lp - rp)
    s = f'<svg viewBox="0 0 {w} {h}" class="svg">'
    for v in (0, 0.4, 0.8, 1.2, 1.6):
        s += f'<line x1="{X(v)}" y1="{top-10}" x2="{X(v)}" y2="{top+rowh*len(rev)-10}" stroke="#E3E9EE"/>'
        s += f'<text x="{X(v)}" y="{top+rowh*len(rev)+8}" font-size="11" text-anchor="middle" fill="{GREY}">RM{v:.1f} mil</text>'
    for i, (n, lo, ba, hi, _) in enumerate(rev):
        y = top + i * rowh + 14
        s += f'<text x="{lp-12}" y="{y+5}" font-size="12.5" font-weight="700" text-anchor="end" fill="{NAVY}">{n}</text>'
        s += f'<line x1="{X(lo)}" y1="{y}" x2="{X(hi)}" y2="{y}" stroke="{TEAL}" stroke-width="10" stroke-linecap="round" opacity="0.35"/>'
        s += f'<circle cx="{X(ba)}" cy="{y}" r="9" fill="{NAVY}"/>'
        s += f'<text x="{X(hi)+14}" y="{y+4}" font-size="11" fill="{GREY}">RM{lo:.2f}-{hi:.2f} mil</text>'
    s += f'<circle cx="{lp}" cy="{h-10}" r="6" fill="{NAVY}"/><text x="{lp+12}" y="{h-6}" font-size="11" fill="{GREY}">Base case</text>'
    s += f'<line x1="{lp+90}" y1="{h-10}" x2="{lp+120}" y2="{h-10}" stroke="{TEAL}" stroke-width="10" opacity="0.35" stroke-linecap="round"/><text x="{lp+128}" y="{h-6}" font-size="11" fill="{GREY}">Low to high range</text>'
    return s + "</svg>"
ra = "".join(f"<tr><td><b>{a}</b></td><td>{e}</td></tr>" for a,_,_,_,e in rev)
P_REVENUE = page(0, "Illustrative revenue scenarios",
  "If the openings are confirmed, four streams could together be worth roughly RM0.9-3 mil a year; these are scenarios, not forecasts",
  f"""<div class="mx">{rev_svg()}</div>
  <div class="h2" style="margin-top:6px">Annual gross revenue, by stream, with the assumptions behind it</div>
  <table class="tbl"><thead><tr><th style="width:30%">Stream</th><th>Key assumptions (monthly unless stated)</th></tr></thead><tbody>{ra}</tbody></table>
  <div class="callout"><b>How to read this:</b> each range is gross revenue before costs, built from planning assumptions. Rates, LLM Corporation's right to charge, and partner interest must all be confirmed in months 1 to 3 before any figure goes into a business case.</div>
  {src("Charging price benchmark around RM1.70/kWh for highway DC charging (Malaysia4u, 2026); tower ground rent benchmark RM1,500 a month on private land (Mudah listing). Other rates are the author's planning assumptions.")}""")

srcs = [
 ("Bernama, 30 Jul 2026: MCMC-LLM to build 77 new telco towers", "https://bernama.com/radio/news.php?id=2588148"),
 ("Kosmo: 77 menara telekomunikasi baharu, LLM sebagai pemudah cara", "https://www.kosmo.com.my/?p=987035"),
 ("Bernama, 12 Nov 2026: KKR identifies R&amp;R site on LTU route in Pahang", "https://bernama.com/en/news.php?id=2633463"),
 ("Carz, Oct 2024: KKR seeking RM20 mil to build R&amp;R along LTU", "https://carz.com.my/2024/10/kkr-seeking-rm20-million-to-build-rr-along-ltu-highway"),
 ("Bernama, 22 Jul 2025: Kelantan plans two R&amp;R stops", "https://bernama.com/en/news.php?id=2447837"),
 ("Bernama, 29 Oct 2026: Kelantan CSR Section 1B progress", "https://bernama.com/en/news.php?id=2627274"),
 ("Bernama, 6 May 2026: NPE traffic and urban highways (LLM DG)", "https://www.bernama.com/bm/news.php/am/sukan/am/news.php?id=2553353"),
 ("Bernama: NPE extension RM1.7 bil, about 6% progress", "https://bernama.com/bm/news.php?id=2572406"),
 ("Bernama, 23 Jun 2026: RM25.2 mil solar LED lights at 32 locations", "https://bernama.com/radio/news.php?id=2571817"),
 ("Bernama, 27 Jul 2026: 18 new motorcycle shelters", "https://bernama.com/bm/am/news.php?id=2586419"),
 ("Bernama, 19 Oct 2026: 50% of highways with smart technology", "https://www.bernama.com/radio/news.php?id=2622663"),
 ("Bernama, 29 Sep 2026: Pan Borneo Sabah progress", "https://bernama.com/bm/news.php?id=2613126"),
 ("Focus Malaysia: Gentari and LLM intercity EV hub at Penchala Link", "https://focusmalaysia.my/?p=237014"),
 ("Carz: PLUS EV chargers, 350 by 2028, Seremban hub", "https://www.carz.com.my/webview/2025/08/plus-surpasses-2025-target-with-112-ev-chargers"),
 ("SoyaCincau, Oct 2026: delays deploying highway EV chargers", "https://soyacincau.com/2026/10/17/shell-recharge-180kw-ev-dc-charger-temerloh-rnr-westbound/"),
 ("Malaysia4u: EV charging prices in Malaysia, 2026", "https://malaysia4u.com/ev-charging-guide"),
 ("Mudah: telco tower land rented at RM1,500 a month", "https://www.mudah.my/pelaburan-hartanah-dengan-pendapatan-sedia-ada-115233817.htm"),
]
sl = "".join(f'<li><a href="{u}">{t}</a><br><span class="url">{u}</span></li>' for t,u in srcs)
P_SOURCES = page(0, "Sources", "All public facts in this plan come from the sources below, accessed 18 November 2026",
  f'<ol class="srcs">{sl}</ol><p class="note">LLM Corporation Sdn. Bhd. has no public profile online; its role in each project is an assumption to confirm.</p>')


# ---------- RISK SECTION ----------
# id, risk, category, likelihood, impact, mitigation, owner, KRI, trigger, plan B
RISKS = [
 ("R1", "LLM Corporation's mandate or right to charge is unclear (e.g. tower access treated as public service, no fee)", "Regulatory", 4, 5,
  "Confirm role and charging rights in writing in month 1; get a legal view before any partner talks", "Manager, Legal",
  "Written confirmation of role per stream", "No confirmation by end of month 1",
  "Pivot to streams the company clearly controls (managed R&amp;R, services, sponsorship); offer facilitation services for a fee"),
 ("R2", "Approvals from LLM, KKR, state or board take longer than planned", "Regulatory", 4, 4,
  "Map approval steps early; submit complete papers; pre-brief approvers", "Executive",
  "Days in approval vs plan", "Any approval 30+ days late",
  "Split the deal into phases that need lower-level approval; run a pilot site first"),
 ("R3", "Low traffic means weak tenant demand at the new Central Spine Road R&amp;R", "Commercial", 4, 3,
  "Short, flexible leases; local SME tenants; festive-season pop-up markets", "Executive",
  "Tenant enquiries and sign-ups vs plan", "Fewer than half the units committed 2 months before opening",
  "Open with core facilities only (toilets, prayer, fuel, 1 convenience store); add stalls as traffic grows"),
 ("R4", "Concessionaires do not cooperate on sites they run", "Stakeholder", 3, 4,
  "Lead with revenue-share models that benefit them; involve LLM's concession unit early", "Manager",
  "Concessionaire responses within 4 weeks", "Two concessionaires decline or do not respond",
  "Focus on sites outside concessions (new state and federal R&amp;Rs, LLM land) first"),
 ("R5", "Land, utility or power constraints (e.g. grid capacity for EV fast chargers)", "Technical", 3, 4,
  "Check land status and power capacity with TNB before offering a site", "Executive, Engineering",
  "Site due-diligence completed per site", "Site fails land or power check",
  "Offer the next site on the shortlist; propose battery-assisted (BESS) chargers to the operator"),
 ("R6", "Partner interest or price is lower than assumed", "Commercial", 3, 3,
  "Test prices in sounding meetings before modelling; keep a broad long-list", "Executive",
  "Interested partners per stream", "Fewer than 2 interested partners per stream by month 3",
  "Re-scope the offer (shorter term, lower entry rent, revenue share) or drop the stream"),
 ("R7", "Contractor or vendor delays and cost overruns on site works", "Delivery", 3, 3,
  "Monthly progress and cost checks against contract; early written notices", "Executive",
  "Schedule and cost variance", "Delay over 4 weeks or cost over 10%",
  "Formal recovery plan from vendor; penalty clauses; replacement vendor from the panel"),
 ("R8", "Procurement or governance breach (e.g. perceived direct award, conflict of interest)", "Compliance", 2, 5,
  "Open tender or RFP; declarations of interest; full documentation and audit trail", "Manager, Procurement",
  "Procurement steps completed and documented", "Any complaint or audit query",
  "Pause the process, refer to integrity and legal units, re-run the selection openly"),
 ("R9", "Safety incident during site works or from roadside installations", "Safety", 2, 5,
  "Safety checklists, inspections, approved traffic management plans", "Contractor, Executive",
  "Inspections done; near-misses reported", "Any incident or repeated near-miss",
  "Stop work on site, investigate, report to LLM, resume only after corrective action"),
 ("R10", "Monsoon floods disrupt works and site visits in Pahang and Kelantan (Nov-Mar)", "External", 3, 3,
  "Schedule east coast site work outside peak monsoon; build float into timelines", "Executive",
  "Weather warnings; days lost", "Official flood warning for a project area",
  "Switch to desk work and partner meetings; move site visits to west coast projects"),
 ("R11", "Budget cuts or policy changes (funding, toll policy, leadership)", "External", 2, 4,
  "Prioritise self-funded, partner-funded models that need little public money", "Manager",
  "Budget and policy announcements", "Funding withdrawn or deferred",
  "Re-package projects as partner-funded concessions or revenue-share deals"),
 ("R12", "Operations workload crowds out business development", "Internal", 3, 2,
  "Automate reporting with AI; protect two days a week for pipeline work", "Executive",
  "Hours on routine reporting per week", "Pipeline not updated for 2 weeks",
  "Agree priorities with manager; delegate or simplify routine reports"),
 ("R13", "Confidential data leaks through AI tools or shared files", "IT &amp; data", 2, 3,
  "Use only approved tools; no confidential data in public AI tools; access controls", "Executive, IT",
  "Tool and access reviews done", "Any suspected data exposure",
  "Revoke access, report to IT, assess and notify as required"),
]
def lvl(sc):
    return ("Critical", "#B23A2E") if sc >= 15 else ("High", "#D9822B") if sc >= 10 else ("Medium", "#E6B84F") if sc >= 5 else ("Low", "#5FBFB5")

def heat_svg():
    cs, x0, y0 = 92, 70, 20
    s = f'<svg viewBox="0 0 {x0+cs*5+20} {y0+cs*5+70}" class="svg">'
    for li in range(1, 6):
        for im in range(1, 6):
            sc = li * im; _, c = lvl(sc)
            x, y = x0 + (li - 1) * cs, y0 + (5 - im) * cs
            s += f'<rect x="{x}" y="{y}" width="{cs-3}" height="{cs-3}" rx="4" fill="{c}" opacity="0.28"/>'
            s += f'<text x="{x+cs-10}" y="{y+16}" font-size="10" text-anchor="end" fill="{GREY}">{sc}</text>'
    cells = {}
    for r in RISKS: cells.setdefault((r[3], r[4]), []).append(r[0])
    for (li, im), ids in cells.items():
        x, y = x0 + (li - 1) * cs, y0 + (5 - im) * cs
        for k, rid in enumerate(ids):
            cx = x + 26 + (k % 3) * 28; cy = y + 38 + (k // 3) * 30
            _, c = lvl(li * im)
            s += f'<circle cx="{cx}" cy="{cy}" r="13" fill="{c}"/><text x="{cx}" y="{cy+4}" font-size="10" font-weight="800" text-anchor="middle" fill="white">{rid}</text>'
    lab = ["Rare", "Unlikely", "Possible", "Likely", "Almost certain"]
    ilab = ["Minor", "Moderate", "Significant", "Major", "Severe"]
    for i in range(5):
        s += f'<text x="{x0+i*cs+cs/2}" y="{y0+cs*5+16}" font-size="10.5" text-anchor="middle" fill="{NAVY}">{i+1} {lab[i]}</text>'
        s += f'<text x="{x0-8}" y="{y0+(4-i)*cs+cs/2+4}" font-size="10.5" text-anchor="end" fill="{NAVY}">{i+1}</text>'
    s += f'<text x="{x0+cs*2.5}" y="{y0+cs*5+40}" font-size="13" font-weight="700" text-anchor="middle" fill="{NAVY}">Likelihood &#8594;</text>'
    s += f'<text transform="translate(18,{y0+cs*2.5}) rotate(-90)" font-size="13" font-weight="700" text-anchor="middle" fill="{NAVY}">Impact &#8594;</text>'
    return s + "</svg>"

P_RISK_HEAT = page(0, "Risk assessment",
  "Thirteen risks were assessed; two are critical and five are high, mostly around approvals, mandate and demand",
  f"""<div class="mx" style="width:125mm;margin:0 auto">{heat_svg()}</div>
  <div class="cols2" style="margin-top:8px"><div><div class="h2">How risks are scored</div>
   <p>Score = <b>likelihood</b> (1 rare to 5 almost certain) &times; <b>impact</b> (1 minor to 5 severe) on revenue, schedule, safety or reputation.</p>
   <table class="tbl band"><tbody>
    <tr><td><span class="lvl" style="background:#B23A2E;color:white">Critical</span></td><td style='white-space:nowrap'>15-25</td><td>Escalate to management within 48 hours; act now</td></tr>
    <tr><td><span class="lvl" style="background:#D9822B;color:white">High</span></td><td style='white-space:nowrap'>10-14</td><td>Named owner, action plan, reviewed monthly</td></tr>
    <tr><td><span class="lvl" style="background:#E6B84F">Medium</span></td><td>5-9</td><td>Monitor through key risk indicators</td></tr>
    <tr><td><span class="lvl" style="background:#5FBFB5;color:white">Low</span></td><td>1-4</td><td>Accept and review each quarter</td></tr></tbody></table></div>
   <div><div class="h2">Top risks to watch</div>
   <ul class="ul"><li><b>R1</b> Mandate and right to charge unclear (20)</li><li><b>R2</b> Approvals slower than planned (16)</li>
   <li><b>R3</b> Weak tenant demand at the new R&amp;R (12)</li><li><b>R4</b> Concessionaires do not cooperate (12)</li><li><b>R5</b> Land or power constraints (12)</li></ul>
  </div></div>
  <p class="note">Scores are the author's initial assessment and will be re-scored with the manager in month 1 and reviewed monthly.</p>
  {src("R3 reflects reports that private investors did not come forward for LTU R&amp;Rs because traffic is low outside festive seasons (Carz, Oct 2024). R5 reflects reported power constraints and red tape in highway EV charger deployment (SoyaCincau, 2023 and Oct 2026).")}""")

def reg_rows(rs):
    out = ""
    for r in rs:
        sc = r[3] * r[4]; n, c = lvl(sc)
        out += f"<tr><td><b>{r[0]}</b></td><td>{r[1]}<div class='cat'>{r[2]}</div></td><td class='c'>{r[3]}</td><td class='c'>{r[4]}</td><td class='c'><span class='lvl' style='background:{c};color:{'white' if n!='Medium' else NAVY}'>{sc} {n}</span></td><td>{r[5]}</td><td>{r[6]}</td></tr>"
    return out
REG_HEAD = "<thead><tr><th style='width:5%'>ID</th><th style='width:28%'>Risk</th><th class='c' style='width:6%'>L</th><th class='c' style='width:6%'>I</th><th class='c' style='width:15%'>Score</th><th>Mitigation (prevent)</th><th style='width:13%'>Owner</th></tr></thead>"
srt = sorted(RISKS, key=lambda r: -r[3]*r[4])
P_REG1 = page(0, "Risk register (1 of 2)",
  "Critical and high risks each have a named owner and a prevention plan from month 1",
  f"<table class='tbl reg'>{REG_HEAD}<tbody>{reg_rows(srt[:7])}</tbody></table><p class='note'>L = likelihood, I = impact, each scored 1 to 5. Owners are proposed and will be agreed with the manager.</p>")
P_REG2 = page(0, "Risk register (2 of 2)",
  "Medium and lower risks are monitored through indicators and reviewed every month",
  f"<table class='tbl reg'>{REG_HEAD}<tbody>{reg_rows(srt[7:])}</tbody></table>")

kr = "".join(f"<tr><td><b>{r[0]}</b></td><td>{r[7]}</td><td>{r[8]}</td><td>{r[9]}</td></tr>" for r in srt)
P_PLANB = page(0, "Contingency plans (Plan B)",
  "Every risk has an early-warning indicator, a clear trigger and a ready Plan B, so a setback changes the route, not the goal",
  f"""<table class="tbl reg pb"><thead><tr><th style="width:5%">ID</th><th style="width:21%">Early-warning indicator</th><th style="width:24%">Trigger for Plan B</th><th>Plan B (contingency)</th></tr></thead><tbody>{kr}</tbody></table>""")

delays = [
 ("Months 1-2", "Onboarding and access", "Slow access to files, contracts and systems; key people on leave in year-end holidays", "Request access lists on day 1; meet people in priority order"),
 ("Months 1-4", "Monsoon season", "Northeast monsoon (Nov-Mar) can flood Pahang and Kelantan sites and roads", "Do east coast site visits in dry windows; keep desk work as backup"),
 ("Months 2-3", "Festive periods", "Chinese New Year and Ramadan to Hari Raya (around Feb-Mar 2027) slow meetings and approvals", "Book partner meetings before the festive period; use it for desk analysis"),
 ("Months 3-6", "Approval cycles", "Management and board meet on fixed dates; a missed cut-off can add a month", "Get the meeting calendar early and work back from paper deadlines"),
 ("Months 4-6", "Tender periods", "An open tender or RFP usually needs several weeks for notice, evaluation and award", "Start tender documents in parallel with the business case"),
 ("Throughout", "Budget timing", "Budget announcements and fiscal year-end can freeze or shift spending", "Prefer partner-funded models; track budget news"),
]
dl = "".join(f"<tr><td><b>{a}</b></td><td><b>{b}</b></td><td>{c}</td><td>{d}</td></tr>" for a,b,c,d in delays)
P_DELAY = page(0, "Delay watch-list",
  "Six predictable delays can be planned around from day one, so the timeline already allows for them",
  f"""<table class="tbl"><thead><tr><th style="width:13%">When</th><th style="width:16%">Delay driver</th><th>What could happen</th><th style="width:30%">How to plan around it</th></tr></thead><tbody>{dl}</tbody></table>
  <div class="h2" style="margin-top:24px">How risk is managed every month</div>
  <div class="chev sm4">
   <div class="cv" style="background:#0B2545"><div class="cvn">Identify</div><div class="cvd">New risks from meetings, site visits and partner talks</div></div>
   <div class="cv" style="background:#2E5A80"><div class="cvn">Assess</div><div class="cvd">Re-score likelihood and impact</div></div>
   <div class="cv" style="background:#0E7C74"><div class="cvn">Respond</div><div class="cvd">Avoid, reduce, transfer or accept; activate Plan B on trigger</div></div>
   <div class="cv" style="background:#13A89E"><div class="cvn">Report</div><div class="cvd">Monthly risk summary to manager; critical within 48 hours</div></div>
  </div>
  <p class="note">Festive dates for 2027 are approximate and assume the role starts in early 2027.</p>""")


# ---------- CONDENSED PAGES ----------
srows2 = ""
for o in sorted(OPPS, key=score, reverse=True):
    cells = "".join(f'<td><span class="dot sm d{v}">{v}</span></td>' for v in o[2:])
    srows2 += f"<tr><td><b>{o[1].replace('&','&amp;')}</b></td>{cells}<td class='tot'>{score(o):.2f}</td></tr>"
P_PRIOR = page(0, "Opportunities and prioritisation",
  "Telco sites, advertising and project services are quick wins; new R&amp;Rs, EV charging and solar are strategic bets",
  f"""<table class="tbl sc cmp"><thead><tr><th>Opportunity</th><th>Revenue<br><small>30%</small></th><th>Speed<br><small>25%</small></th><th>Ease of approval<br><small>20%</small></th><th>Mandate fit<br><small>15%</small></th><th>Low risk<br><small>10%</small></th><th>Score</th></tr></thead><tbody>{srows2}</tbody></table>
  <div class="mx" style="width:150mm;margin:12px auto 0">{matrix_svg()}</div>
  <p class="note">Scored 1 (weak) to 5 (strong); bubble size = weighted score. Indicative desk scores, to be re-scored with real data in month 2.</p>""")

P_ROAD = page(0, "Approach and roadmap",
  "Three phases over six months: diagnose the business, organise and test, then propose and close",
  chevrons([("MONTH 1", "Diagnose", "Learn the business, take over projects and contracts, map stakeholders, collect ideas", NAVY),
            ("MONTHS 2-3", "Organise &amp; test", "Weekly reporting, contract register, screen ideas, test the strongest with partners", "#2E5A80"),
            ("MONTHS 4-6", "Propose &amp; close", "Business cases, legal and finance review, management approval, MOU or tender", TEAL)]).replace('class="chev"','class="chev sm4"') +
  '<div style="margin-top:18px">' + gantt() + """</div><div class="legend"><span><i style="background:#0B2545"></i>Operations &amp; contracts</span><span><i style="background:#13A89E"></i>Business development</span><span><i style="background:#E0A458"></i>Stakeholders</span><span><i style="background:#7A8FA3"></i>Digital &amp; AI</span><span><i class="dia"></i>Milestone</span></div>
  <div class="callout">Each phase ends with a gate review with my manager: what was delivered, what was learned, and whether to continue, change or stop each workstream. Partners are reached warm first: companies already applying to LLM, introductions through LLM and concessionaires, then a targeted short list.</div>""")

rr2 = ""
for r in srt:
    sc = r[3]*r[4]; n, c = lvl(sc)
    rr2 += f"<tr><td><b>{r[0]}</b></td><td>{r[1]}</td><td class='c'><span class='lvl' style='background:{c};color:{'white' if n!='Medium' else NAVY}'>{sc}</span></td><td>{r[5]}</td><td><span class='trg'>If: {r[8]}</span><br>{r[9]}</td></tr>"
P_RISKPB = page(0, "Risk register and Plan B",
  "Every risk has a prevention plan, a clear trigger and a ready Plan B, so a setback changes the route, not the goal",
  f"""<table class="tbl reg rpb"><thead><tr><th style="width:5%">ID</th><th style="width:25%">Risk</th><th class='c' style="width:7%">Score</th><th style="width:27%">Prevent</th><th>Plan B (trigger, then action)</th></tr></thead><tbody>{rr2}</tbody></table>
  <p class="note">Predictable delays are built into the timeline: east coast monsoon (Nov-Mar), Chinese New Year and Ramadan to Hari Raya (around Feb-Mar 2027), board cut-off dates and tender periods. Risks are reviewed monthly; critical ones go to management within 48 hours.</p>""")

hz_small = '<div class="hzs">' + "".join(
  f'<div class="hcs" style="border-top:5px solid {c}"><b style="color:{c}">{h}</b> &middot; <span class="ht2">{t}</span><br>{d}</div>'
  for h,t,d,c in [("Horizon 1","Months 0-6","Monetise existing assets: telco sites, advertising, services, new R&amp;R operation",TEAL),
                  ("Horizon 2","Months 6-18","Scale partnerships: EV charging network, R&amp;R tenants, multi-year agreements","#3E5C76"),
                  ("Horizon 3","Months 18-36","New platforms: solar on highway land, traffic data products, recurring revenue",GOLD)]) + '</div>'
sl2 = "".join(f'<li><a href="{u}">{t}</a></li>' for t,u in srcs)
P_END = page(0, "Next steps and sources",
  "Four questions to confirm with management will turn this plan into an agreed work programme",
  f"""<ol class="ul">
   <li>What are the company's current revenue sources and this year's revenue target?</li>
   <li>Which assets and rights can the company commercialise alone, and which need concessionaire or LLM approval?</li>
   <li>What are the agreed KPIs for this role, and is any pay linked to revenue?</li>
   <li>How much field work and travel does the role involve, and who does it report to?</li></ol>
  <div class="h2" style="margin-top:16px">Beyond six months</div>{hz_small}
  <div class="why">Why me: 4+ years in audit, risk and stakeholder work; seminars delivered for 9 government and corporate organisations; and daily use of AI to build reports, trackers and internal data platforms at Malaysia Productivity Corporation.</div>
  <div class="h2" style="margin-top:16px">Sources (accessed 18 November 2026)</div>
  <ol class="srcs2">{sl2}</ol>""")

CSS = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: 'Inter', sans-serif; color:{NAVY}; font-size:13px; line-height:1.5; }}
.page {{ width:210mm; height:297mm; padding:16mm 15mm 14mm; position:relative; page-break-after:always; overflow:hidden; background:white; }}
.top {{ display:flex; justify-content:space-between; font-size:9.5px; letter-spacing:1.2px; text-transform:uppercase; color:{GREY}; border-bottom:2px solid {TEAL}; padding-bottom:6px; }}
.sec {{ color:{TEAL}; font-weight:700; }}
h1 {{ font-size:24px; line-height:1.27; margin:20px 0 8px; font-weight:700; letter-spacing:-0.2px; }}
.sub {{ color:{GREY}; margin:0 0 10px; }}
.body {{ margin-top:18px; }}
.foot {{ position:absolute; left:15mm; right:15mm; bottom:9mm; display:flex; justify-content:space-between; font-size:9px; color:{GREY}; border-top:1px solid #D7DEE5; padding-top:5px; }}
.h2 {{ font-size:15px; font-weight:700; margin-bottom:8px; }}
.h2.t {{ color:#0E7C74; }} .h2.g {{ color:#A86A1C; }}
p {{ margin:0 0 6px; }}
.lead {{ margin-bottom:12px; }}
.note {{ font-size:10.5px; color:{GREY}; margin-top:10px; font-style:italic; }}
.ul {{ margin:0; padding-left:17px; }} .ul li {{ margin-bottom:5px; }} .ul.sm li {{ margin-bottom:3px; }}
.cols2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.cols3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:14px; margin-top:24px; }}
.card {{ background:{LIGHT}; border-radius:6px; padding:16px 16px; }}
.ct {{ font-weight:700; font-size:14px; margin-bottom:6px; }}
.callout {{ margin-top:26px; font-size:13.5px; border-left:4px solid {TEAL}; background:#F3FAF9; padding:15px 18px; border-radius:0 6px 6px 0; }}
.tiles {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }}
.tile {{ background:{NAVY}; color:white; border-radius:6px; padding:20px 14px; }}
.big {{ font-size:26px; font-weight:800; color:{GOLD}; line-height:1; }}
.lab {{ font-size:12px; margin-top:8px; opacity:.92; }}
.tbl {{ width:100%; border-collapse:collapse; font-size:12.8px; }}
.tbl th {{ background:{NAVY}; color:white; text-align:left; padding:11px 11px; font-weight:600; font-size:12px; vertical-align:bottom; }}
.tbl td {{ padding:12px 11px; border-bottom:1px solid #DCE3EA; vertical-align:top; }}
.tbl tr:nth-child(even) td {{ background:#F7F9FB; }}
.tbl .c, .sc td, .sc th {{ text-align:center; }} .sc td:first-child, .sc th:first-child {{ text-align:left; }}
.tbl td.hi {{ font-weight:700; color:#0E7C74; }}
.tot {{ font-weight:800; font-size:12.5px; color:#0E7C74; }}
.dot {{ display:inline-block; width:30px; height:30px; line-height:30px; border-radius:50%; font-weight:700; font-size:11px; }}
.d1 {{ background:#F1F1F1; color:#999; }} .d2 {{ background:#DCE7EF; }} .d3 {{ background:#B6CDDD; }} .d4 {{ background:#5FBFB5; color:white; }} .d5 {{ background:#0E7C74; color:white; }}
.chev {{ display:flex; gap:4px; }}
.cv {{ flex:1; color:white; padding:16px 26px 16px 22px; clip-path:polygon(0 0, 90% 0, 100% 50%, 90% 100%, 0 100%, 8% 50%); min-height:210px; }}
.cv:first-child {{ clip-path:polygon(0 0, 90% 0, 100% 50%, 90% 100%, 0 100%); }}
.cvw {{ font-size:9.5px; letter-spacing:1.2px; opacity:.85; }} .cvn {{ font-size:21px; font-weight:800; margin:4px 0 6px; }} .cvd {{ font-size:12.5px; line-height:1.4; }}
.stake {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }}
.sk {{ border:1.5px solid #C5D2DD; border-radius:8px; padding:20px 12px; text-align:center; font-weight:700; font-size:13px; }}
.sk small {{ font-weight:400; color:{GREY}; font-size:11.5px; }}
.sk.core {{ background:{NAVY}; color:white; border-color:{NAVY}; }} .sk.core small {{ color:#C9D6E2; }}
.mx {{ background:white; }} .svg {{ width:100%; font-family:Inter; }}
.qw {{ display:flex; gap:12px; background:#F3FAF9; border-radius:6px; padding:15px 13px; margin-bottom:12px; font-size:12.5px; }}
.qw span {{ flex:none; width:28px; height:28px; border-radius:50%; background:{TEAL}; color:white; font-weight:800; text-align:center; line-height:28px; }}
.qw.c {{ background:#FCF5EA; }} .qw.c span {{ background:{GOLD}; }}
.gantt {{ display:grid; grid-template-columns:120px repeat(6,1fr); row-gap:0; border-top:1px solid #DCE3EA; }}
.gm {{ font-size:11.5px; font-weight:700; color:{GREY}; text-align:center; padding:7px 0; border-left:1px dashed #DCE3EA; }}
.gl {{ font-size:12.5px; font-weight:700; padding:18px 6px 0 0; border-top:1px solid #DCE3EA; height:78px; }}
.gr {{ grid-column:span 6; position:relative; border-top:1px solid #DCE3EA; height:78px;
       background-image:linear-gradient(to right, #E6ECF1 1px, transparent 1px); background-size:16.6667% 100%; }}
.gb {{ position:absolute; top:14px; height:30px; border-radius:4px; color:white; font-size:10.5px; font-weight:600; padding:0 7px; line-height:30px; white-space:nowrap; overflow:hidden; margin-left:2px; }}
.gd {{ position:absolute; top:48px; width:12px; height:12px; background:{GOLD}; transform:rotate(45deg); border:2px solid white; box-shadow:0 0 0 1px {GOLD}; }}
.gdt {{ position:absolute; top:62px; width:100px; text-align:center; font-size:10.5px; color:{GREY}; }}
.legend {{ display:flex; gap:16px; flex-wrap:wrap; font-size:11px; color:{GREY}; margin-top:10px; }}
.legend i {{ display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:5px; vertical-align:-2px; }}
.legend i.dia {{ background:{GOLD}; transform:rotate(45deg) scale(.8); }}
.fun {{ align-items:center; }}
.funnel {{ display:flex; flex-direction:column; align-items:center; gap:5px; }}
.fs {{ color:white; text-align:center; padding:17px 4px; border-radius:4px; }}
.fv {{ display:block; font-size:24px; font-weight:800; line-height:1; }} .fn {{ font-size:11.5px; }}
.stg {{ border-left:3px solid {TEAL}; padding:8px 0 8px 12px; margin-bottom:14px; font-size:13px; }}
.hz {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; align-items:start; }}
.hc {{ background:{LIGHT}; border-radius:0 0 6px 6px; padding:16px; min-height:300px; }}
.hh {{ font-weight:800; font-size:19px; }} .ht {{ font-size:10px; color:{GREY}; letter-spacing:1px; text-transform:uppercase; margin:2px 0 6px; }}
.hd {{ font-weight:700; margin-bottom:8px; }} .hc ul {{ margin:0; padding-left:16px; }} .hc li {{ margin-bottom:7px; font-size:12.5px; }}
.lvl {{ padding:3px 9px; border-radius:10px; font-size:11px; white-space:nowrap; font-weight:700; }}
.lvl.high {{ background:#F8D9D4; color:#A1342A; }} .lvl.medium {{ background:#FBEBD2; color:#A86A1C; }} .lvl.low {{ background:#D6F0EC; color:#0E7C74; }}
.why {{ margin-top:26px; background:{NAVY}; color:white; padding:18px 18px; font-size:13.5px; border-radius:6px; }}
.src {{ font-size:9.5px; color:{GREY}; margin-top:12px; }}
.st {{ background:#E6F2F1; color:#0E7C74; padding:3px 8px; border-radius:10px; font-size:10.5px; font-weight:700; white-space:nowrap; }}
.chev.sm4 .cv {{ min-height:120px; padding:14px 22px 14px 26px; }}
.chev.sm4 .cvn {{ font-size:15px; }}
.srcs {{ padding-left:20px; font-size:11.5px; }} .srcs li {{ margin-bottom:7px; }} .srcs a {{ color:{NAVY}; font-weight:600; text-decoration:none; }}
.url {{ color:{GREY}; font-size:9.5px; word-break:break-all; }}
.reg td {{ font-size:11.5px; padding:9px 9px; }} .reg th {{ font-size:11px; }}
.pb td {{ font-size:11px; padding:8px 8px; }}
.cat {{ font-size:9.5px; color:{GREY}; margin-top:3px; text-transform:uppercase; letter-spacing:.6px; }}
.rk {{ grid-template-columns:1.05fr 1fr; align-items:start; }}
.band td {{ padding:7px 6px; font-size:11.5px; }}
.cmp td {{ padding:5px 8px; }} .cmp th {{ padding:7px 8px; }}
.dot.sm {{ width:22px; height:22px; line-height:22px; font-size:10px; }}
.rpb td {{ font-size:10.3px; padding:6px 7px; line-height:1.35; }} .rpb th {{ font-size:10.5px; padding:7px; }}
.trg {{ color:#A86A1C; font-weight:700; }}
.hzs {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px; }}
.hcs {{ background:{LIGHT}; padding:10px 11px; font-size:11.5px; border-radius:0 0 6px 6px; }} .ht2 {{ color:{GREY}; font-size:10.5px; }}
.srcs2 {{ columns:2; column-gap:18px; padding-left:18px; font-size:9.6px; margin:0; }} .srcs2 li {{ margin-bottom:3px; break-inside:avoid; }} .srcs2 a {{ color:{NAVY}; text-decoration:none; }}
.cover {{ padding:0; background:{NAVY}; color:white; }}
.cband {{ position:absolute; left:0; top:0; width:10mm; height:100%; background:{TEAL}; }}
.ctext {{ position:absolute; left:24mm; right:20mm; top:40mm; }}
.ckick {{ font-size:11px; letter-spacing:2.5px; color:{GOLD}; font-weight:700; }}
.ctitle {{ font-size:38px; font-weight:800; line-height:1.12; margin:14px 0 14px; letter-spacing:-0.6px; }}
.csub {{ font-size:15px; line-height:1.45; color:#C9D6E2; max-width:150mm; }}
.cline {{ width:40mm; height:3px; background:{GOLD}; margin:24px 0 18px; }}
.cby {{ font-size:12px; line-height:1.6; color:#C9D6E2; }} .cby b {{ color:white; font-size:14px; }}
.cart {{ position:absolute; left:0; right:0; bottom:28mm; width:100%; }}
.cnote {{ position:absolute; left:24mm; right:20mm; bottom:10mm; font-size:9px; color:#8FA5B9; }}
"""

order = [pages[0], pages[1], P_PROJECTS, P_PRIOR, P_SPOT, P_PARTNERS, P_REVENUE, P_ROAD, pages[7], P_RISK_HEAT, P_RISKPB, P_END]
pages = order
_body = "".join(pages)
_tot = _body.count("__PG__")
_k = [1]
import re as _re
def _num(m):
    _k[0] += 1
    return f"{_k[0]} / {_tot + 1}"
_body = _re.sub("__PG__", _num, _body)
html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{_body}</body></html>"
open("output/proposal.html", "w").write(html)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.set_content(html); pg.wait_for_timeout(300)
    pg.pdf(path="output/6-Month_Plan_Proposal.pdf", format="A4", print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}); b.close()
print("built", len(pages), "pages")
