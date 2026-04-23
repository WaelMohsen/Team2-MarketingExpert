// Shared UI primitives — premium edition
// Refined palette, better shadows, richer typography, tabular numerals throughout.

const mkTokens = {
  // Surfaces — layered warm paper with true depth
  bg: '#EFEBE2',              // slightly deeper paper for contrast against surface
  bgDeep: '#E8E3D7',
  surface: '#FBF9F3',         // not pure white — warmer, more expensive
  surfaceRaised: '#FFFFFF',
  surfaceInk: '#111510',      // dark surface for contrast moments

  // Type
  ink: '#0E100C',
  ink2: '#3C3F38',
  ink3: '#7C7F74',
  ink4: '#A8AA9E',
  inkInv: '#F1EEE3',

  // Lines — two weights for better hierarchy
  line: '#DFDBCE',
  line2: '#EBE7DB',
  lineDark: '#23251F',

  // Brand — deeper forest, richer soft
  accent: '#183E2E',
  accentDark: '#0E2A1E',
  accentSoft: '#DFE8E0',
  accentGlow: 'rgba(24,62,46,0.10)',

  // Semantic
  warn: '#8A4A0B',
  warnSoft: '#F0E0C6',
  danger: '#7A221C',
  dangerSoft: '#EED0CC',
  ok: '#235832',
  okSoft: '#D4E3D5',

  // Shadows — layered, warm-tinted (not gray)
  shadowSm: '0 1px 0 rgba(30,22,8,0.04), 0 1px 2px rgba(30,22,8,0.04)',
  shadowMd: '0 1px 0 rgba(30,22,8,0.04), 0 4px 12px -2px rgba(30,22,8,0.08)',
  shadowLg: '0 2px 0 rgba(30,22,8,0.05), 0 12px 32px -8px rgba(30,22,8,0.14)',
  shadowInset: 'inset 0 1px 0 rgba(255,255,255,0.6)',
};

function MkLogo({ size = 22 }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
      <svg width={size+2} height={size+2} viewBox="0 0 34 34" fill="none">
        <rect x="1" y="1" width="32" height="32" rx="8" fill={mkTokens.ink}/>
        <rect x="1" y="1" width="32" height="32" rx="8" fill="url(#lg)" opacity="0.5"/>
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2A2D26"/>
            <stop offset="1" stopColor="#0E100C"/>
          </linearGradient>
        </defs>
        <path d="M9 23V11l8 9 8-9v12" stroke="#F1EEE3" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        <circle cx="28" cy="8" r="1.6" fill="#7BC694"/>
      </svg>
      <span style={{ fontFamily:'"Instrument Serif", Georgia, serif', fontSize: size+2, color: mkTokens.ink, letterSpacing:'-0.015em', lineHeight:1 }}>
        Marketing Desk
      </span>
    </div>
  );
}

function MkPill({ tone='neutral', children, style, dot }) {
  const map = {
    neutral:{ bg:'#F1EDE0', fg:mkTokens.ink2, border:'#E4E0D2', dot:'#8A8C7E' },
    high:   { bg:mkTokens.dangerSoft, fg:mkTokens.danger, border:'#E2C4BF', dot:mkTokens.danger },
    medium: { bg:mkTokens.warnSoft, fg:mkTokens.warn, border:'#E4D2B3', dot:mkTokens.warn },
    low:    { bg:mkTokens.okSoft, fg:mkTokens.ok, border:'#C1D4C3', dot:mkTokens.ok },
    accent: { bg:mkTokens.accentSoft, fg:mkTokens.accent, border:'#C3D4C7', dot:mkTokens.accent },
    dark:   { bg:mkTokens.lineDark, fg:'#E8E5D8', border:mkTokens.lineDark, dot:'#7BC694' }
  };
  const s = map[tone] || map.neutral;
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:6,
      fontSize:10.5, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.09em',
      padding:'3.5px 9px 3px', borderRadius:999,
      background:s.bg, color:s.fg, border:`1px solid ${s.border}`,
      fontVariantNumeric:'tabular-nums',
      ...style
    }}>
      {dot && <span style={{ width:5, height:5, borderRadius:99, background:s.dot, display:'inline-block' }}/>}
      {children}
    </span>
  );
}

function MkStat({ label, value, sub, accent, big, delta }) {
  return (
    <div style={{
      padding:'20px 22px 18px', background:mkTokens.surface,
      border:`1px solid ${mkTokens.line}`, borderRadius:14,
      display:'flex', flexDirection:'column', gap:8,
      minHeight: big ? 136 : 112,
      boxShadow: mkTokens.shadowSm,
      position:'relative', overflow:'hidden'
    }}>
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div style={{
          fontSize:10.5, fontWeight:600, letterSpacing:'0.12em',
          textTransform:'uppercase', color:mkTokens.ink3
        }}>{label}</div>
        {delta != null && (
          <span style={{
            fontSize:11, fontWeight:600, fontVariantNumeric:'tabular-nums',
            color: delta >= 0 ? mkTokens.ok : mkTokens.danger,
            display:'inline-flex', alignItems:'center', gap:3
          }}>
            <svg width="9" height="9" viewBox="0 0 10 10" style={{ transform: delta >= 0 ? 'none' : 'rotate(180deg)' }}>
              <path d="M5 1l4 5H1l4-5z" fill="currentColor"/>
            </svg>
            {delta >= 0 ? '+' : ''}{delta}%
          </span>
        )}
      </div>
      <div style={{
        fontFamily:'"Instrument Serif", Georgia, serif',
        fontSize: big ? 48 : 36, lineHeight:1.02,
        color: accent || mkTokens.ink, letterSpacing:'-0.028em',
        fontVariantNumeric:'tabular-nums',
        fontFeatureSettings:'"ss01"'
      }}>{value}</div>
      {sub && <div style={{ fontSize:12, color:mkTokens.ink3, fontVariantNumeric:'tabular-nums' }}>{sub}</div>}
    </div>
  );
}

function MkSection({ title, kicker, right, children, style }) {
  return (
    <section style={{ marginBottom:32, ...style }}>
      <div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between', marginBottom:16, gap:16 }}>
        <div>
          {kicker && (
            <div style={{
              fontSize:10.5, fontWeight:600, letterSpacing:'0.14em',
              textTransform:'uppercase', color:mkTokens.ink3, marginBottom:6,
              display:'inline-flex', alignItems:'center', gap:8
            }}>
              <span style={{ width:14, height:1, background:mkTokens.ink3, display:'inline-block' }}/>
              {kicker}
            </div>
          )}
          <h2 style={{
            margin:0, fontFamily:'"Instrument Serif", Georgia, serif',
            fontWeight:400, fontSize:30, color:mkTokens.ink, letterSpacing:'-0.02em', lineHeight:1.1
          }}>{title}</h2>
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

function MkIconBtn({ children, onClick, title, active }) {
  return (
    <button onClick={onClick} title={title} style={{
      width:34, height:34, display:'inline-flex', alignItems:'center', justifyContent:'center',
      background: active ? mkTokens.ink : mkTokens.surface,
      border:`1px solid ${active ? mkTokens.ink : mkTokens.line}`,
      borderRadius:9, color: active ? mkTokens.inkInv : mkTokens.ink2,
      cursor:'pointer', boxShadow: mkTokens.shadowSm,
      transition:'all 120ms ease'
    }}>{children}</button>
  );
}

// Subtle grain/noise background — adds texture without looking busy
function MkGrain() {
  return (
    <svg style={{ position:'fixed', inset:0, width:'100%', height:'100%', pointerEvents:'none', zIndex:0, opacity:0.35, mixBlendMode:'multiply' }}>
      <filter id="grain">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
        <feColorMatrix values="0 0 0 0 0.05  0 0 0 0 0.05  0 0 0 0 0.03  0 0 0 0.04 0"/>
      </filter>
      <rect width="100%" height="100%" filter="url(#grain)"/>
    </svg>
  );
}

function MkDivider({ label }) {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:14, margin:'28px 0' }}>
      <div style={{ flex:1, height:1, background:mkTokens.line }}/>
      {label && (
        <span style={{
          fontSize:10.5, fontWeight:600, letterSpacing:'0.14em', textTransform:'uppercase',
          color:mkTokens.ink3
        }}>{label}</span>
      )}
      <div style={{ flex:1, height:1, background:mkTokens.line }}/>
    </div>
  );
}

function fmtMoney(n){ if(typeof n!=='number') return n; return '$'+n.toLocaleString('en-US',{maximumFractionDigits:0}); }
function fmtNum(n){ if(typeof n!=='number') return n; return n.toLocaleString('en-US',{maximumFractionDigits:0}); }
function fmtPct(n){ if(typeof n!=='number') return n; return n.toFixed(2)+'%'; }
function fmtCompact(n){ if(typeof n!=='number') return n;
  if (Math.abs(n) >= 1e6) return (n/1e6).toFixed(1)+'M';
  if (Math.abs(n) >= 1e3) return (n/1e3).toFixed(1)+'k';
  return n.toString();
}

Object.assign(window, { mkTokens, MkLogo, MkPill, MkStat, MkSection, MkIconBtn, MkGrain, MkDivider, fmtMoney, fmtNum, fmtPct, fmtCompact });
