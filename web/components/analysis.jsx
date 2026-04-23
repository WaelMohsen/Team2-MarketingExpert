// Analysis + Recommendations — premium edition

function MkConfidenceBar({ value }) {
  return (
    <div>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:8 }}>
        <span style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3 }}>Model confidence</span>
        <span style={{ fontFamily:'"Instrument Serif", Georgia, serif', fontSize:22, color:mkTokens.ink, fontVariantNumeric:'tabular-nums', letterSpacing:'-0.02em' }}>{value}<span style={{ fontSize:13, color:mkTokens.ink3 }}>%</span></span>
      </div>
      <div style={{ height:6, background:mkTokens.line2, borderRadius:99, overflow:'hidden', position:'relative', boxShadow:'inset 0 1px 0 rgba(0,0,0,0.04)' }}>
        <div style={{
          width:value+'%', height:'100%',
          background:`linear-gradient(90deg, ${mkTokens.accent} 0%, ${mkTokens.accentDark} 100%)`,
          borderRadius:99, transition:'width 900ms cubic-bezier(0.2,0.8,0.2,1)'
        }}/>
      </div>
      <div style={{ display:'flex', justifyContent:'space-between', marginTop:6, fontSize:10.5, color:mkTokens.ink4, fontVariantNumeric:'tabular-nums' }}>
        <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
      </div>
    </div>
  );
}

function MkSignalList({ title, items, tone='neutral', dense, count }) {
  if (!items || !items.length) return null;
  const cfg = {
    danger:{ color:mkTokens.danger, bg:mkTokens.dangerSoft, icon:<path d="M10 2L2 16h16L10 2z" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinejoin="round"/> },
    warn:  { color:mkTokens.warn,   bg:mkTokens.warnSoft,   icon:<><circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M10 6v4M10 13.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></> },
    ok:    { color:mkTokens.ok,     bg:mkTokens.okSoft,     icon:<path d="M3 10l4 4 10-10" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/> }
  }[tone] || { color:mkTokens.ink2, bg:'#F1EDE0', icon:<circle cx="10" cy="10" r="3" fill="currentColor"/> };
  return (
    <div style={{ padding:'16px 18px', background:mkTokens.surface, border:`1px solid ${mkTokens.line}`, borderRadius:13, boxShadow: mkTokens.shadowSm }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ width:22, height:22, borderRadius:6, background:cfg.bg, color:cfg.color, display:'inline-flex', alignItems:'center', justifyContent:'center' }}>
            <svg width="12" height="12" viewBox="0 0 20 20">{cfg.icon}</svg>
          </span>
          <span style={{ fontSize:11, fontWeight:600, letterSpacing:'0.11em', textTransform:'uppercase', color:mkTokens.ink2 }}>{title}</span>
        </div>
        <span style={{ fontSize:11, color:mkTokens.ink3, fontVariantNumeric:'tabular-nums' }}>{items.length}</span>
      </div>
      <ul style={{ listStyle:'none', padding:0, margin:0, display:'flex', flexDirection:'column', gap:10 }}>
        {items.map((t,i)=>(
          <li key={i} style={{ fontSize:13, color:mkTokens.ink, lineHeight:1.5, display:'flex', gap:10 }}>
            <span style={{ flexShrink:0, marginTop:7, width:5, height:5, borderRadius:99, background:cfg.color }}/>
            <span>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MkChannelTable({ rows }) {
  const cols = [
    { k:'channel', label:'Channel', w:'17%' },
    { k:'spend', label:'Spend', w:'12%', fmt:fmtMoney },
    { k:'revenue', label:'Revenue', w:'16%', fmt:fmtMoney },
    { k:'conversions', label:'Conv.', w:'10%', fmt:fmtNum },
    { k:'ctr', label:'CTR', w:'10%', fmt:v=>v.toFixed(2)+'%' },
    { k:'cpa', label:'CPA', w:'9%', fmt:fmtMoney },
    { k:'roas', label:'ROAS', w:'10%', fmt:v=>v.toFixed(2)+'×' },
    { k:'bounce', label:'Bounce', w:'8%', fmt:v=>(v*100).toFixed(0)+'%' },
    { k:'churn', label:'Churn', w:'8%', fmt:v=>(v*100).toFixed(0)+'%' }
  ];
  const maxRevenue = Math.max(...rows.map(r=>r.revenue));
  const maxRoas = Math.max(...rows.map(r=>r.roas));
  return (
    <div style={{ background:mkTokens.surface, border:`1px solid ${mkTokens.line}`, borderRadius:14, overflow:'hidden', boxShadow: mkTokens.shadowSm }}>
      <div style={{
        display:'flex', padding:'13px 20px',
        background:`linear-gradient(180deg, #F4EFE0 0%, #F0EBD9 100%)`,
        borderBottom:`1px solid ${mkTokens.line}`,
        fontSize:10.5, fontWeight:600, letterSpacing:'0.11em', textTransform:'uppercase', color:mkTokens.ink3
      }}>
        {cols.map(c => <div key={c.k} style={{ width:c.w, textAlign: c.k==='channel' ? 'left':'right' }}>{c.label}</div>)}
      </div>
      {rows.map((r,i)=>{
        const roasTone = r.roas >= maxRoas * 0.9 ? mkTokens.ok : r.roas < 5 ? mkTokens.warn : mkTokens.ink;
        return (
          <div key={r.channel} style={{
            display:'flex', padding:'15px 20px', alignItems:'center',
            borderBottom: i<rows.length-1 ? `1px solid ${mkTokens.line2}` : 'none',
            fontSize:13, color:mkTokens.ink, transition:'background 120ms'
          }}
          onMouseEnter={e=>e.currentTarget.style.background='#FBF9F0'}
          onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
            {cols.map(c => {
              const v = r[c.k];
              if (c.k==='channel') {
                return (
                  <div key={c.k} style={{ width:c.w, fontWeight:600, display:'flex', alignItems:'center', gap:10 }}>
                    <span style={{ width:6, height:6, borderRadius:99, background:mkTokens.accent }}/>
                    {v}
                  </div>
                );
              }
              if (c.k==='revenue') {
                const pct = (v/maxRevenue)*100;
                return (
                  <div key={c.k} style={{ width:c.w, textAlign:'right', position:'relative' }}>
                    <span style={{ fontVariantNumeric:'tabular-nums', fontWeight:500 }}>{c.fmt(v)}</span>
                    <div style={{ height:3, background:mkTokens.line2, borderRadius:99, marginTop:5, overflow:'hidden' }}>
                      <div style={{ width: pct+'%', height:'100%', background:`linear-gradient(90deg, ${mkTokens.accent}, ${mkTokens.accentDark})`, borderRadius:99, marginLeft:'auto' }}/>
                    </div>
                  </div>
                );
              }
              if (c.k==='roas') {
                return <div key={c.k} style={{ width:c.w, textAlign:'right', fontVariantNumeric:'tabular-nums', color: roasTone, fontWeight:600 }}>{c.fmt(v)}</div>;
              }
              return <div key={c.k} style={{ width:c.w, textAlign:'right', fontVariantNumeric:'tabular-nums' }}>{c.fmt ? c.fmt(v) : v}</div>;
            })}
          </div>
        );
      })}
    </div>
  );
}

function MkRecommendationCard({ rec, idx, open, onToggle }) {
  const priority = (rec.priority||'medium').toLowerCase();
  const tone = priority==='high' ? 'high' : priority==='medium' ? 'medium' : 'low';
  const accentColor = priority==='high' ? mkTokens.danger : priority==='medium' ? mkTokens.warn : mkTokens.ok;
  return (
    <article style={{
      background:mkTokens.surface, border:`1px solid ${open ? mkTokens.ink : mkTokens.line}`,
      borderRadius:16, overflow:'hidden',
      boxShadow: open ? mkTokens.shadowLg : mkTokens.shadowSm,
      transition:'all 180ms ease'
    }}>
      <header onClick={onToggle} style={{
        padding:'22px 24px', cursor:'pointer', display:'flex', gap:20,
        alignItems:'flex-start',
        borderBottom: open ? `1px solid ${mkTokens.line2}` : 'none',
        position:'relative'
      }}>
        {/* priority rail */}
        <div style={{ position:'absolute', left:0, top:16, bottom:16, width:3, background:accentColor, borderRadius:'0 2px 2px 0' }}/>

        <div style={{
          width:40, height:40, borderRadius:10,
          background:`linear-gradient(180deg, ${mkTokens.surfaceRaised}, #F5F0E0)`,
          border:`1px solid ${mkTokens.line}`, flexShrink:0,
          display:'flex', alignItems:'center', justifyContent:'center',
          fontFamily:'"Instrument Serif", Georgia, serif', fontSize:20, color:mkTokens.ink,
          boxShadow: mkTokens.shadowInset
        }}>{idx+1}</div>

        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:8, flexWrap:'wrap' }}>
            <MkPill tone={tone} dot>{priority} priority</MkPill>
            <span style={{ fontSize:11, color:mkTokens.ink3, fontWeight:500 }}>{rec.category}</span>
            <span style={{ fontSize:11, color:mkTokens.ink4 }}>·</span>
            <span className="mono" style={{ fontSize:11, color:mkTokens.ink3 }}>{rec.id}</span>
          </div>
          <h3 style={{
            margin:'0 0 8px', fontFamily:'"Instrument Serif", Georgia, serif',
            fontWeight:400, fontSize:24, color:mkTokens.ink, letterSpacing:'-0.02em', lineHeight:1.18
          }}>{rec.title}</h3>
          <p style={{ margin:0, fontSize:14, color:mkTokens.ink2, lineHeight:1.6 }}>{rec.whats_happening}</p>
          <div style={{ display:'flex', gap:18, marginTop:14, fontSize:11.5, color:mkTokens.ink3, flexWrap:'wrap', textTransform:'uppercase', letterSpacing:'0.06em' }}>
            <span><b style={{ color:mkTokens.ink, fontWeight:600 }}>Effort</b> {rec.effort}</span>
            <span><b style={{ color:mkTokens.ink, fontWeight:600 }}>Impact</b> {rec.time_to_see_impact}</span>
            <span><b style={{ color:mkTokens.ink, fontWeight:600 }}>Confidence</b> {rec.confidence}</span>
            <span><b style={{ color:mkTokens.ink, fontWeight:600 }}>Owner</b> {rec.owner_suggestion}</span>
          </div>
        </div>
        <div style={{
          flexShrink:0, color:mkTokens.ink2, marginTop:4,
          width:32, height:32, borderRadius:8,
          border:`1px solid ${mkTokens.line}`, background:mkTokens.surfaceRaised,
          display:'flex', alignItems:'center', justifyContent:'center'
        }}>
          <svg width="14" height="14" viewBox="0 0 16 16" style={{ transform: open ? 'rotate(180deg)' : 'none', transition:'transform 220ms cubic-bezier(0.2,0.8,0.2,1)' }}>
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </header>

      {open && (
        <div style={{ padding:'24px', display:'grid', gridTemplateColumns:'1fr 1fr', gap:18, background:'#FAF6EA' }}>
          <div style={{ gridColumn:'1 / -1' }}>
            <div style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:8 }}>Why this matters</div>
            <p style={{ margin:0, fontSize:15, color:mkTokens.ink, lineHeight:1.65, fontFamily:'"Instrument Serif", Georgia, serif' }}>{rec.why_this_matters}</p>
          </div>

          <div style={{ gridColumn:'1 / -1', padding:'16px 20px', borderRadius:12, background:`linear-gradient(180deg, ${mkTokens.accentSoft}, #D8E4DB)`, border:`1px solid #BACBBE`, display:'flex', gap:14, alignItems:'flex-start', boxShadow: mkTokens.shadowInset }}>
            <div style={{ width:28, height:28, borderRadius:7, background:mkTokens.accent, color:mkTokens.inkInv, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
              <svg width="14" height="14" viewBox="0 0 20 20"><path d="M3 10l4 4 10-10" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            <div style={{ fontSize:13.5, color:mkTokens.ink, lineHeight:1.55 }}>
              <b style={{ textTransform:'uppercase', fontSize:10.5, letterSpacing:'0.1em', color:mkTokens.accent, display:'block', marginBottom:3 }}>Expected impact · {rec.expected_impact?.primary_kpi} → {rec.expected_impact?.direction}</b>
              {rec.expected_impact?.explanation}
            </div>
          </div>

          <div style={{ background:mkTokens.surface, padding:'16px 18px', borderRadius:12, border:`1px solid ${mkTokens.line}` }}>
            <div style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:10 }}>Evidence</div>
            <ul style={{ listStyle:'none', padding:0, margin:0, display:'flex', flexDirection:'column', gap:8 }}>
              {(rec.evidence||[]).map((e,i)=>(
                <li key={i} style={{ fontSize:13, color:mkTokens.ink, lineHeight:1.5, display:'flex', gap:10 }}>
                  <span style={{ flexShrink:0, marginTop:7, width:5, height:5, borderRadius:99, background:mkTokens.ink2 }}/>{e}
                </li>
              ))}
            </ul>
          </div>

          <div style={{ background:mkTokens.surface, padding:'16px 18px', borderRadius:12, border:`1px solid ${mkTokens.line}` }}>
            <div style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:10 }}>Risks & Dependencies</div>
            <ul style={{ listStyle:'none', padding:0, margin:0, display:'flex', flexDirection:'column', gap:8 }}>
              {(rec.dependency_or_risk||[]).map((e,i)=>(
                <li key={i} style={{ fontSize:13, color:mkTokens.ink, lineHeight:1.5, display:'flex', gap:10 }}>
                  <span style={{ flexShrink:0, marginTop:7, width:5, height:5, borderRadius:99, background:mkTokens.warn }}/>{e}
                </li>
              ))}
            </ul>
          </div>

          <div style={{ gridColumn:'1 / -1' }}>
            <div style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:12 }}>Action steps</div>
            <ol style={{ listStyle:'none', padding:0, margin:0, display:'flex', flexDirection:'column', gap:10 }}>
              {(rec.what_you_should_do||[]).map((step,i)=>(
                <li key={i} style={{ padding:'16px 18px', background:mkTokens.surface, border:`1px solid ${mkTokens.line}`, borderRadius:12, boxShadow: mkTokens.shadowSm }}>
                  <div style={{ display:'flex', alignItems:'flex-start', gap:14 }}>
                    <div style={{
                      width:26, height:26, borderRadius:99,
                      background:`linear-gradient(180deg, ${mkTokens.ink}, #1A1D16)`,
                      color:mkTokens.inkInv, fontSize:11.5, fontWeight:600,
                      display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
                      fontVariantNumeric:'tabular-nums', boxShadow: mkTokens.shadowSm
                    }}>{i+1}</div>
                    <div style={{ flex:1 }}>
                      <div style={{ fontSize:14.5, fontWeight:600, color:mkTokens.ink, marginBottom:6, letterSpacing:'-0.005em' }}>{step.step}</div>
                      <div style={{ fontSize:13, color:mkTokens.ink2, lineHeight:1.6 }}>
                        <b style={{ color:mkTokens.ink, fontWeight:600 }}>Where</b> · {step.where} &nbsp;·&nbsp; <b style={{ color:mkTokens.ink, fontWeight:600 }}>How</b> · {step.how}
                      </div>
                      {step.guardrails?.length > 0 && (
                        <div style={{ marginTop:10, display:'flex', gap:6, flexWrap:'wrap' }}>
                          {step.guardrails.map((g,j)=>(
                            <span key={j} style={{
                              fontSize:11, padding:'4px 10px 3px',
                              background:'#FBF9F0', border:`1px solid ${mkTokens.line}`,
                              borderRadius:99, color:mkTokens.ink2,
                              display:'inline-flex', alignItems:'center', gap:5
                            }}>
                              <svg width="9" height="9" viewBox="0 0 10 10"><path d="M2 5l2 2 4-4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/></svg>
                              {g}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          {rec.measurement_plan && (
            <div style={{ gridColumn:'1 / -1', padding:'18px 22px', border:`1px dashed ${mkTokens.line}`, borderRadius:12, background:'transparent' }}>
              <div style={{ fontSize:10.5, fontWeight:600, letterSpacing:'0.12em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:12 }}>Measurement plan</div>
              <div style={{ display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:18, fontSize:13 }}>
                {[
                  ['How to measure', rec.measurement_plan.how_to_measure],
                  ['Success criteria', rec.measurement_plan.success_criteria],
                  ['Check timing', rec.measurement_plan.check_timing]
                ].map(([k,v])=>(
                  <div key={k}>
                    <div style={{ color:mkTokens.ink3, fontSize:10.5, marginBottom:4, letterSpacing:'0.1em', textTransform:'uppercase', fontWeight:600 }}>{k}</div>
                    <div style={{ color:mkTokens.ink, lineHeight:1.5 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

Object.assign(window, { MkConfidenceBar, MkSignalList, MkChannelTable, MkRecommendationCard });
