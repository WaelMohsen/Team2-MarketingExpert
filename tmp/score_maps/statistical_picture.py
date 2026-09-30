from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import math

out=Path('output/diagrams'); out.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(2600,3460),'#FFFFFF'); d=ImageDraw.Draw(im)
regular='C:/Windows/Fonts/arial.ttf'; bold='C:/Windows/Fonts/arialbd.ttf'
ink='#16344A'; line='#718696'
def font(size,b=False): return ImageFont.truetype(bold if b else regular,size)
def text_center(x,y,lines,size=32,color=ink,b=False):
    for i,t in enumerate(lines.split('\n')):
        d.text((x,y+i*(size+12)),t,font=font(size,b),fill=color,anchor='mt')
def box(x,y,w,h,title,body='',fill='#EDF4F8'):
    d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill=fill,outline='#C3D3DE',width=3)
    text_center(x+w/2,y+22,title,34,b=True)
    if body:text_center(x+w/2,y+77,body,31)
def arrow(points,label=None,at=None):
    d.line(points,fill=line,width=5,joint='curve')
    x,y=points[-1]; px,py=points[-2]; a=math.atan2(y-py,x-px)
    d.polygon([(x,y),(x-19*math.cos(a-.45),y-19*math.sin(a-.45)),(x-19*math.cos(a+.45),y-19*math.sin(a+.45))],fill=line)
    if label: d.text(at,label,font=font(29,True),fill=ink)

text_center(1300,55,'Statistical Calculation and Performance Decision',55,b=True)
text_center(1300,135,'score_level  /  fit_beta_prior  /  _score',32,color='#526A7D')
box(540,230,1350,200,'1  Check calculation conditions','Trials > 0  •  Benchmark available\nPeer count meets minimum_peer_entities')
box(1990,245,560,190,'Insufficient evidence','Keep default estimates\nDecision: insufficient_evidence',fill='#F4F1ED')
arrow([(1890,330),(1990,330)],'No',(1910,283))
arrow([(1215,430),(1215,495)],'Yes',(1235,447))
box(540,495,1350,185,'2  Calculate the peer mean','mean = (total peer successes + 0.5)\n÷ (total peer trials + 1)')
arrow([(1215,680),(1215,730)])
box(540,730,1350,225,'3  Determine prior strength','Start with average peer sample size.\nAdjust using variation between peer success rates.\nMinimum strength = 1.')
arrow([(1215,955),(1215,1005)])
box(540,1005,1350,185,'4  Build the Beta prior','alpha = mean × strength\nbeta = (1 − mean) × strength')
arrow([(1215,1190),(1215,1240)])
box(540,1240,1350,150,'5  Generate a reproducible seed','Use level, entity_id and metric to initialize sampling.')
arrow([(1215,1390),(1215,1440)])
box(540,1440,1350,185,'6  Add the entity evidence','posterior_alpha = alpha + successes\nposterior_beta = beta + trials − successes')
arrow([(1215,1625),(1215,1675)])
box(540,1675,1350,185,'7  Calculate the corrected rate','corrected_rate = posterior_alpha\n÷ (posterior_alpha + posterior_beta)')
arrow([(1215,1860),(1215,1910)])
box(540,1910,1350,185,'8  Simulate plausible rates','5,000 entity draws from the posterior\n5,000 benchmark draws from the prior')
arrow([(1215,2095),(1215,2140),(650,2140),(650,2190)])
arrow([(1215,2140),(1880,2140),(1880,2190)])
box(90,2190,1120,190,'9a  Entity rate interval','range_low = 2.5th percentile\nrange_high = 97.5th percentile of entity draws')
box(1310,2190,1140,190,'9b  Favorable lift for each pair','Higher is better: entity − benchmark\nLower is better: benchmark − entity')
arrow([(1880,2380),(1880,2435)])
box(1310,2435,1140,265,'10  Summarize comparison','expected_lift = average lift\nprobability_better = fraction of positive lifts\nlift_low / lift_high = percentiles 2.5 / 97.5\nbenchmark = prior mean')
arrow([(1880,2700),(1880,2750),(1300,2750),(1300,2800)])
box(540,2800,1520,140,'11  Apply ordered statistical rules','Use the lift interval, not probability_better alone.')
for x,cx in [(70,450),(920,1300),(1770,2150)]:
    arrow([(1300,2940),(1300,2980),(cx,2980),(cx,3030)])
box(70,3030,760,220,'SCALE','lift_low > 0\nClear evidence of\noutperformance',fill='#EAF5EF')
box(920,3030,760,220,'KILL','Otherwise, lift_high < 0\nClear evidence of\nunderperformance',fill='#FBEFEE')
box(1770,3030,760,220,'HOLD','Otherwise\nThe lift interval includes\nor touches zero',fill='#FFF6E5')
text_center(1300,3300,'These are statistical decisions, not final recommendations.',32,b=True)
text_center(1300,3350,'Final actions also check evidence sufficiency, benchmark quality and efficiency.',29)
im.save(out/'Statistical_Calculation_and_Performance_Decision.png',dpi=(300,300))
im.resize((1040,1384)).save('tmp/score_maps/statistical_preview.png')
print(out/'Statistical_Calculation_and_Performance_Decision.png')
