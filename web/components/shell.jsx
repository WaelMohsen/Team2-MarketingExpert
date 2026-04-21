// Left rail + category picker — premium edition

function MkSidebar({ view, setView, campaign, setCampaign, campaigns }) {
  const items = [
    { id:'home',    label:'Analyze',    icon: <path d="M3 13l4-4 4 4 5-5 5 5" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round"/> },
    { id:'history', label:'History',    icon: <path d="M4 6h12M4 10h12M4 14h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/> },
    { id:'data',    label:'Data',       icon: <path d="M4 5h12v3H4zM4 9h12v3H4zM4 13h12v3H4z" stroke="currentColor" strokeWidth="1.4" fill="none"/> },
    { id:'chat', label:'Ask Expert',    icon: <path d="M4 4h12v9H9l-3 3v-3H4z" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinejoin="round"/> },
    { id:'settings',label:'Settings',   icon: <><circle cx="10" cy="10" r="2.2" stroke="currentColor" strokeWidth="1.5" fill="none"/><path d="M10 3v2M10 15v2M3 10h2M15 10h2M5 5l1.5 1.5M13.5 13.5L15 15M5 15l1.5-1.5M13.5 6.5L15 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></> }
  ];
  return (
    <aside style={{
      width:248, flexShrink:0, borderRight:`1px solid ${mkTokens.line}`,
      background:'linear-gradient(180deg, #F6F2E6 0%, #F1ECDD 100%)',
      display:'flex', flexDirection:'column',
      padding:'24px 18px 20px', position:'sticky', top:0, height:'100vh',
      zIndex:2
    }}>
      <MkLogo/>

      <div style={{ marginTop:32, fontSize:10.5, fontWeight:600, letterSpacing:'0.14em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:12, paddingLeft:4 }}>Workspace</div>
      <nav style={{ display:'flex', flexDirection:'column', gap:3 }}>
        {items.map(it => (
          <button key={it.id} onClick={()=>setView(it.id)} style={{
            display:'flex', alignItems:'center', gap:11,
            padding:'9px 11px', borderRadius:9, cursor:'pointer',
            background: view===it.id ? mkTokens.surfaceRaised : 'transparent',
            border: view===it.id ? `1px solid ${mkTokens.line}` : '1px solid transparent',
            color: view===it.id ? mkTokens.ink : mkTokens.ink2,
            fontWeight: view===it.id ? 600 : 500,
            fontSize:13, textAlign:'left', letterSpacing:'-0.005em',
            boxShadow: view===it.id ? mkTokens.shadowSm : 'none',
            transition:'all 140ms ease'
          }}>
            <svg width="17" height="17" viewBox="0 0 20 20" style={{ opacity: view===it.id ? 1 : 0.75 }}>{it.icon}</svg>
            {it.label}
            {view===it.id && <span style={{ marginLeft:'auto', width:4, height:4, borderRadius:99, background:mkTokens.accent }}/>}
          </button>
        ))}
      </nav>

      <div style={{ marginTop:28, fontSize:10.5, fontWeight:600, letterSpacing:'0.14em', textTransform:'uppercase', color:mkTokens.ink3, marginBottom:12, paddingLeft:4 }}>Campaign</div>
      <div style={{
        border:`1px solid ${mkTokens.line}`, borderRadius:11, background:mkTokens.surfaceRaised,
        padding:'12px 14px', boxShadow: mkTokens.shadowSm
      }}>
        <div style={{ fontSize:10.5, color:mkTokens.ink3, marginBottom:4, letterSpacing:'0.08em', textTransform:'uppercase' }}>Active</div>
        <select value={campaign} onChange={e=>setCampaign(e.target.value)} style={{
          width:'100%', border:'none', outline:'none', background:'transparent',
          fontSize:14, fontWeight:600, color:mkTokens.ink, padding:0, cursor:'pointer',
          letterSpacing:'-0.01em', appearance:'none'
        }}>
          {campaigns.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <div style={{ marginTop:10, fontSize:11, color:mkTokens.ink3, display:'flex', justifyContent:'space-between', fontVariantNumeric:'tabular-nums' }}>
          <span>Jan 02 — Apr 15</span>
          <span>104d</span>
        </div>
      </div>

      <div style={{ flex:1 }}/>

      <div style={{
        padding:'14px 14px', borderRadius:12,
        background:`linear-gradient(180deg, ${mkTokens.ink} 0%, #1A1D16 100%)`,
        color:mkTokens.inkInv, fontSize:12, position:'relative', overflow:'hidden',
        boxShadow: mkTokens.shadowMd
      }}>
        <div style={{ position:'absolute', top:-20, right:-20, width:80, height:80, borderRadius:99, background:mkTokens.accent, opacity:0.25, filter:'blur(20px)' }}/>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:6, position:'relative' }}>
          <span style={{ fontWeight:600, letterSpacing:'-0.005em' }}>Pipeline</span>
          <span style={{ display:'inline-flex', alignItems:'center', gap:5, fontSize:11, opacity:0.85 }}>
            <span style={{ width:6, height:6, borderRadius:99, background:'#7BC694', boxShadow:'0 0 6px #7BC694' }}/>
            Live
          </span>
        </div>
        <div style={{ opacity:0.72, fontSize:11, fontVariantNumeric:'tabular-nums', position:'relative' }}>GPT-4o · schema v2 · 11.2s avg</div>
      </div>
    </aside>
  );
}

function MkCategoryCard({ cat, selected, onClick }) {
  return (
    <button onClick={onClick} style={{
      textAlign:'left', cursor:'pointer',
      background: selected
        ? `linear-gradient(180deg, ${mkTokens.surfaceRaised} 0%, ${mkTokens.surface} 100%)`
        : mkTokens.surface,
      border: selected ? `1px solid ${mkTokens.ink}` : `1px solid ${mkTokens.line}`,
      borderRadius:18, padding:'24px 24px 22px',
      boxShadow: selected ? `${mkTokens.shadowLg}, 0 0 0 3px ${mkTokens.accentGlow}` : mkTokens.shadowSm,
      position:'relative', transition:'all 200ms cubic-bezier(0.2, 0.8, 0.2, 1)',
      display:'flex', flexDirection:'column', gap:14, minHeight:200,
      transform: selected ? 'translateY(-2px)' : 'none',
      overflow:'hidden'
    }}>
      {/* subtle accent glow in top-right */}
      {selected && (
        <div style={{ position:'absolute', top:-30, right:-30, width:120, height:120, borderRadius:99, background:cat.tint, filter:'blur(32px)', opacity:0.8 }}/>
      )}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', position:'relative' }}>
        <div style={{
          width:40, height:40, borderRadius:11,
          background: `linear-gradient(180deg, ${cat.tint} 0%, ${cat.tintDeep || cat.tint} 100%)`,
          display:'flex', alignItems:'center', justifyContent:'center', color: cat.ink,
          border: `1px solid ${cat.border || 'transparent'}`,
          boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.7)'
        }}>
          <svg width="19" height="19" viewBox="0 0 20 20" fill="none">{cat.icon}</svg>
        </div>
        <span className="mono" style={{ fontSize:10.5, color:mkTokens.ink3, letterSpacing:'0.12em' }}>{cat.code}</span>
      </div>
      <div style={{ position:'relative' }}>
        <div style={{
          fontFamily:'"Instrument Serif", Georgia, serif', fontSize:26, color:mkTokens.ink,
          letterSpacing:'-0.02em', lineHeight:1.12, marginBottom:8
        }}>{cat.title}</div>
        <div style={{ fontSize:13, color:mkTokens.ink2, lineHeight:1.5 }}>{cat.blurb}</div>
      </div>
      <div style={{ marginTop:'auto', display:'flex', alignItems:'center', justifyContent:'space-between', fontSize:11.5, color:mkTokens.ink3, position:'relative', paddingTop:12, borderTop:`1px solid ${mkTokens.line2}` }}>
        <span style={{ fontVariantNumeric:'tabular-nums' }}>{cat.kpiCount} KPIs · {cat.recCount} recs</span>
        <span style={{
          display:'inline-flex', alignItems:'center', gap:5,
          color: selected ? mkTokens.accent : mkTokens.ink2,
          fontWeight: selected ? 600 : 500
        }}>
          {selected ? 'Selected' : 'Analyze'}
          <svg width="11" height="11" viewBox="0 0 12 12"><path d="M3 6h6m0 0L6 3m3 3L6 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" fill="none"/></svg>
        </span>
      </div>
    </button>
  );
}

// Mini sparkline chart for hero moment
function MkSparkChart({ data, height = 120, accent }) {
  const w = 600, h = height, pad = 8;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = (w - pad*2) / (data.length - 1);
  const pts = data.map((v,i) => [pad + i*step, pad + (h - pad*2) * (1 - (v - min)/range)]);
  const path = pts.map((p,i) => (i===0?'M':'L') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  const area = path + ` L ${pts[pts.length-1][0]} ${h-pad} L ${pts[0][0]} ${h-pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width:'100%', height }} preserveAspectRatio="none">
      <defs>
        <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={accent || mkTokens.accent} stopOpacity="0.18"/>
          <stop offset="1" stopColor={accent || mkTokens.accent} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <path d={area} fill="url(#sparkFill)"/>
      <path d={path} stroke={accent || mkTokens.accent} strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      {pts.map((p,i) => i===pts.length-1 && (
        <g key={i}>
          <circle cx={p[0]} cy={p[1]} r="5" fill={mkTokens.surface}/>
          <circle cx={p[0]} cy={p[1]} r="3" fill={accent || mkTokens.accent}/>
        </g>
      ))}
    </svg>
  );
}

Object.assign(window, { MkSidebar, MkCategoryCard, MkSparkChart });
