from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf/MVP_Pipeline_Architecture.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
W,H = 842,595
c = canvas.Canvas(str(OUT), pagesize=(W,H))
c.setTitle('MVP Pipeline Architecture | Awareness Analysis')
c.setAuthor('Team2 MarketingExpert')
ink='#172D43'; teal='#087E8B'; blue='#EAF2FA'; green='#E8F5F1'; gray='#526477'

def txt(x,y,text,size=10,color=ink,bold=False):
    c.setFillColor(HexColor(color)); c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    c.drawString(x,y,text)

def para(x,top,w,text,size=10,color=ink):
    p=Paragraph(text,ParagraphStyle('p',fontName='Helvetica',fontSize=size,leading=size*1.35,textColor=HexColor(color)))
    _,h=p.wrap(w,500); p.drawOn(c,x,top-h); return h

def box(x,y,w,h,title,lines=(),fill=blue):
    c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor('#CDDAE5'))
    c.roundRect(x,y,w,h,8,fill=1,stroke=1)
    txt(x+12,y+h-20,title,11,bold=True)
    for i,line in enumerate(lines): txt(x+12,y+h-37-i*14,line,9,gray)

def arrow(points,color=teal,dashed=False):
    c.setStrokeColor(HexColor(color)); c.setFillColor(HexColor(color)); c.setLineWidth(1.5)
    c.setDash(4,3) if dashed else c.setDash()
    p=c.beginPath(); p.moveTo(*points[0])
    for pt in points[1:]: p.lineTo(*pt)
    c.drawPath(p); c.setDash()
    x,y=points[-1]; a,b=points[-2]; import math
    ang=math.atan2(y-b,x-a); p=c.beginPath();p.moveTo(x,y)
    p.lineTo(x-7*math.cos(ang-.45),y-7*math.sin(ang-.45));p.lineTo(x-7*math.cos(ang+.45),y-7*math.sin(ang+.45));p.close();c.drawPath(p,fill=1,stroke=0)

def header(n,title,subtitle):
    c.setFillColor(HexColor(ink)); c.rect(0,H-9,W,9,fill=1,stroke=0)
    txt(34,554,'TEAM2 / MARKETING EXPERT / SRC_MVP',9,teal,True)
    txt(34,521,title,25,bold=True); txt(34,499,subtitle,10,gray)
    c.setStrokeColor(HexColor('#DCE4EB'));c.line(34,35,808,35)
    txt(34,20,'Architecture guide | 01_OUTCOME_AWARENESS_Analysis.ipynb',8,gray)
    txt(766,20,f'{n} / 3',8,gray)

header(1,'End-to-end pipeline','run_mvp() orchestrates all objectives. The notebook then filters and presents Awareness results.')
box(34,375,232,95,'INPUT DATA',['meta_data.json: ads and delivery','conversations.json: chats and outcomes','conversation_signals_v3_paid.jsonl'])
box(304,375,232,95,'1-2. Load and normalize',['data.py','load_cycle()','load_conversation_signals()'])
box(574,375,234,95,'3. Build raw scorecards',['scorecards.py / build_scorecards()','Counts, spend, rates and diagnostics','Five entity levels'])
arrow([(266,421),(304,421)]);arrow([(536,421),(574,421)])
box(574,232,234,100,'4. Score primary performance',['statistics.py / score_all_levels()','Peers, Bayesian scores, uncertainty','Efficiency and recommended actions'])
arrow([(691,375),(691,332)])
box(304,232,232,100,'5. Score conversation quality',['semantics.py / add_semantic_scores()','Uses normalized chats + loaded signals','Separate quality score and audit log'],green)
arrow([(574,282),(536,282)])
box(34,232,232,100,'6. Allocate campaign budgets',['allocation.py / allocate_budget()','Objective envelopes and campaign shares','Proposed tests for funded test campaigns'],green)
arrow([(304,282),(266,282)])
box(34,89,232,100,'7. Package recommendations',['packet.py','build_recommendation_input()','Structured evidence, actions and budgets'])
arrow([(150,232),(150,189)])
box(304,89,232,100,'8. Optional LLM report',['recommendation.py / run_recommendation()','Enabled only with with_llm=True','Disabled in the Awareness notebook'])
arrow([(266,138),(304,138)],dashed=True)
box(574,89,234,100,'9. Save and return',['JSON / JSONL files in outputs/','MVPResult returned to Python','Notebook tables and charts'])
arrow([(536,138),(574,138)],dashed=True)
arrow([(150,89),(150,69),(691,69),(691,89)])
txt(278,53,'Solid route: default execution    Dashed route: optional report generation',8,gray)
txt(34,351,'Configuration: objectives.yaml defines scoring rules; budget_policy.yaml defines budget allocation.',9,gray)
c.showPage()

header(2,'Awareness: scores, actions and budgets','Three distinct outputs: performance estimates, action labels, and budget allocations.')
box(34,393,224,77,'Primary outcome',['Link CTR = link clicks / impressions','Higher is better'])
box(302,393,230,77,'Empirical Bayes comparison',['Select compatible peers; exclude self','Estimate corrected CTR and uncertainty'])
arrow([(258,432),(302,432)])
box(582,393,226,77,'Performance estimate',['Corrected CTR','95% credible range'])
arrow([(532,432),(582,432)])
box(302,268,230,80,'Statistical decision',['Positive lift range: SCALE','Negative: KILL; crosses zero: HOLD'])
arrow([(373,393),(373,348)])
box(34,268,224,80,'Efficiency and evidence',['CPM vs same-objective peer median','Evidence sufficiency + benchmark quality'])
box(34,145,224,82,'Recommended action',['SCALE / KEEP_AS_TEST','DO_NOT_FUND','INSUFFICIENT_EVIDENCE'])
arrow([(146,268),(146,227)])
arrow([(302,308),(280,308),(280,186),(258,186)])
box(582,268,226,80,'Primary probability component',['probability_better','Fraction of simulated positive lifts'])
arrow([(489,393),(489,369),(696,369),(696,348)])
box(302,145,230,82,'Conversation quality component',['Ad alignment in selected mature chats','Separate Bayesian quality estimate','Use semantic 95% lower bound'],green)
box(582,145,226,82,'Campaign priority',['probability_better','x semantic range_low'],green)
arrow([(696,268),(696,227)]);arrow([(532,187),(582,187)])
box(582,60,226,57,'Campaign budget',['Objective envelope x normalized priority'],green)
arrow([(695,145),(695,117)])
para(34,120,495,'<b>Current implementation:</b> action labels do not gate budget allocation. The allocator uses the two score components above. Missing either component gives zero allocation; an objective with no positive priorities remains unallocated.',10)
c.showPage()

header(3,'Reading the architecture','Execution details, policy boundaries and the objects returned to the notebook.')
txt(34,462,'SCORING RULES',11,teal,True)
items=[
('Primary benchmark','Use at least two valid same-objective peers. Awareness may fall back to compatible Awareness + Engagement Link CTR peers. That fallback is provisional and caps assessable actions at KEEP_AS_TEST.'),
('Conversation quality','Select the earliest mature conversation per customer within each entity before checking labels. Awareness success means ad alignment supported by message evidence. Unknown and missing labels are excluded from assessable trials.'),
('Semantic benchmark','Use same-objective peers only. If peers are insufficient, use Beta(0.5, 0.5) smoothing and show a range without a peer-comparison claim.'),
('Budget policy','Total configured budget: 100 units. Preserve each objective\'s previous spend share, then allocate its envelope using normalized priority products. The product is a policy index, not a joint probability or an optimal return estimate.')]
y=443
for title,body in items:
    txt(34,y,title,10,bold=True); h=para(34,y-9,370,body,9.5);y-=h+29
txt(448,462,'NOTEBOOK INTERFACE',11,teal,True)
box(448,355,360,88,'run_mvp() returns MVPResult',['data: normalized source data','scorecards: campaign, adset, ad, creative, audience','semantic_evidence: conversation selection audit'])
box(448,255,360,88,'Decision and recommendation objects',['allocations: campaign budget records','exploration_tests: proposed next-cycle tests','recommendation_input / optional recommendation_output'])
para(448,238,360,'<b>Notebook behavior:</b> the first code cell runs the complete pipeline and writes outputs. Later cells primarily display results for OUTCOME_AWARENESS; some reconstruct calculations for explanation.',10)
txt(448,161,'SAVED OUTPUTS',11,teal,True)
para(448,144,360,'entity_scorecards.jsonl<br/>semantic_evidence.jsonl<br/>campaign_budget.json<br/>exploration_tests.json<br/>recommendation_input.json<br/>recommendation_output.json (only when generated)',9.5)
para(34,87,370,'<b>Scope:</b> completed-cycle analysis. CTR is a response proxy, not proof of brand-awareness lift. This guide describes the reviewed code; it does not execute campaigns or validate extracted labels.',9)
txt(34,43,'Source: src_mvp/pipeline.py, statistics.py, semantics.py, allocation.py and config/*.yaml',8,gray)
c.save()
reader=PdfReader(str(OUT))
assert len(reader.pages)==3
assert all(len(page.extract_text())>500 for page in reader.pages)
print(OUT)
