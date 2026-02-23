import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import csv, re, io
from collections import defaultdict
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="TTS Amazon Lift Model", page_icon="📊", layout="wide")

BG='#07090E';S1='#0D1017';S2='#141820';BD='#1C2030'
RED='#FF3B52';GRN='#00E5A0';YEL='#FFB020';BLU='#4DA6FF'
PUR='#B07CFF';T1='#E8EAF0';T2='#7B8098';T3='#3E4460'
CC={'HIGH':GRN,'MED':YEL,'LOW':'#FF8C42','WEAK':RED,'INSUF':T3}
MO=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=DM+Sans:wght@400;500;700;800&display=swap');
.stApp{{background:{BG};}}
section[data-testid="stSidebar"]{{background:{S1};border-right:1px solid {BD};}}
h1,h2,h3{{font-family:'DM Sans',sans-serif!important;color:{T1}!important;}}
.kpi{{background:{S1};border:1px solid {BD};border-radius:10px;padding:16px;text-align:center;}}
.kpi .lb{{font:800 10px 'JetBrains Mono',monospace;color:{T2};text-transform:uppercase;letter-spacing:.1em;}}
.kpi .vl{{font:800 26px 'JetBrains Mono',monospace;color:{T1};letter-spacing:-.03em;}}
.kpi .vg{{font:800 26px 'JetBrains Mono',monospace;color:{GRN};letter-spacing:-.03em;}}
.kpi .sb{{font:400 10px 'JetBrains Mono',monospace;color:{T3};margin-top:2px;}}
.btag{{display:inline-block;background:{S2};border:1px solid {BD};border-radius:6px;padding:3px 10px;margin:2px;font:700 11px 'DM Sans',sans-serif;color:{T1};}}
.btag-new{{border-color:{YEL};background:rgba(255,176,32,.06);}}
.stTabs [data-baseweb="tab-list"]{{gap:4px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;border:1px solid {BD};border-radius:6px;padding:5px 14px;font-size:11px;font-weight:700;color:{T2};}}
.stTabs [aria-selected="true"]{{background:rgba(255,59,82,.08)!important;border-color:{RED}!important;color:{RED}!important;}}
</style>""", unsafe_allow_html=True)

def fd(v):
    if v is None: return "$0"
    v=float(v)
    if abs(v)>=1e6:return f"${v/1e6:.1f}M"
    if abs(v)>=1e3:return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"
def fn(v):
    if v is None: return "0"
    v=float(v)
    if v>=1e6:return f"{v/1e6:.1f}M"
    if v>=1e3:return f"{v/1e3:.0f}K"
    return f"{v:,.0f}"
def sf(v):
    try:return float(str(v).replace('$','').replace(',','').replace('%',''))
    except:return 0.0
def kpi_html(lb,vl,sb="",g=False):
    vc="vg" if g else "vl"
    return f'<div class="kpi"><div class="lb">{lb}</div><div class="{vc}">{vl}</div><div class="sb">{sb}</div></div>'
def sec(t):
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:28px 0 10px;"><div style="width:3px;height:16px;background:{RED};border-radius:2px;"></div><span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.12em;">{t}</span></div>',unsafe_allow_html=True)
def badge_html(c):
    return f'<span style="display:inline-block;font:800 9px \'JetBrains Mono\',monospace;padding:2px 8px;border-radius:3px;letter-spacing:.06em;background:{CC.get(c,T3)}15;color:{CC.get(c,T3)};">{c}</span>'
def pthem(fig,h=350):
    fig.update_layout(height=h,plot_bgcolor=BG,paper_bgcolor=BG,font=dict(family='JetBrains Mono,monospace',color=T2,size=10),margin=dict(l=10,r=10,t=20,b=10),hovermode='x unified',legend=dict(orientation='h',y=-0.12,font=dict(size=10)))
    fig.update_xaxes(gridcolor=BD,showline=False);fig.update_yaxes(gridcolor=BD,showline=False)
    return fig

BRAND_MAP={
    'Thorne Health Shop':'Thorne Research','Pure Encapsulations Shop':'Pure Encapsulations',
    'Hims & Hers':'Hims & Hers','Vital Proteins Shop':'Vital Proteins',
    'youtheory':'YouTheory','Philips Shop US':'Philips','PHILIPS':'Philips',
    'TruNiagen':'Tru Niagen','SmartMouth':'SmartMouth','Sakura of America Shop':'Sakura',
    'Strider Bikes':'Strider Bikes','Mercola Market Shop':'Dr. Mercola',
    'Natural Factors':'Natural Factors','Herbs, Etc.':'Herbs, Etc.',
    'Amazing Grass':'Amazing Grass','Emerald Labs':'Emerald Labs',
    'Balance of Nature Shop':'Balance of Nature','AdvoCare':'AdvoCare',
    'Brownmed':'Brownmed','New Chapter Inc':'New Chapter',
    'Optimum Nutrition Shop':'Optimum Nutrition','Gaia Herbs':'Gaia',
    'MegaFood Shop':'MegaFood','MuscleTech':'MuscleTech',
    'CeraVe':'CeraVe','Murad Skincare':'Murad','SuavecitoPomade':'Suavecito',
    'OLLY Wellness':'OLLY','Zenwise Health':'Zenwise',
    'livehumann':'Humann','Rocco & Roxie Supply Co.':'Rocco & Roxie',
    'Flora Health Shop':'Flora Health','Urban Decay Cosmetics':'Urban Decay',
    'urban decay':'Urban Decay','Isopure':'Isopure','Dr. Tobias':'Dr. Tobias',
    'Leatherman Tools':'Leatherman','PBfit':'PBfit','Brutus Broth':'Brutus Broth',
    'GET ONNIT':'Onnit','The Genius Brand Shop':'The Genius Brand',
    'Integrative Therapeutics':'Integrative Therapeutics','Baby Brezza':'Baby Brezza',
    'Weider Global Nutrition':'Weider','CureHydration':'Cure Hydration',
    'G2G Bar':'G2G Bar','Life Extension Supplements':'Life Extension',
    'Azzaro Parfums':'Azzaro','Azzaro':'Azzaro','K9 Feline Natural':'K9 Natural',
    'Shop at BeLive':'BeLive','Barimelts':'Barimelts','EZMelts':'EZ Melts',
    'SIXSTAR PRO':'SixStar','Elevate organic':'Elevate Organic',
    'Fanttik':'Fanttik','Fanttik Prime':'Fanttik','FanttikSolo':'Fanttik',
    'Atrium - Pure Encapsulations':'Pure Encapsulations','Dr Mercola':'Dr. Mercola',
    'Emerald Laboratories':'Emerald Labs','Herbs Etc.':'Herbs, Etc.',
    'Glanbia Performance Nutrition':'Optimum Nutrition',
    'Philips Avent':'Philips','Philips Norelco':'Philips','Philips Sonicare':'Philips',
    'Strider':'Strider Bikes','Youtheory':'YouTheory',
    'Advocare':'AdvoCare','Olly':'OLLY','Humann':'Humann',
    'Fazit Beauty':'Fazit','Kradle My Pet':'Kradle','Cosyuree Beauty':'Cosyuree',
    'Luseta Beauty':'Luseta Beauty',"Renzo's Vitamins":"Renzo's Vitamins",
    'Seeking Health':'Seeking Health','Keeps':'Keeps','TruFru':'TruFru',
}

def norm(name, bm):
    if not name or not str(name).strip(): return None
    name = str(name).strip()
    if name in bm: return bm[name]
    for k, v in bm.items():
        if k.lower() == name.lower(): return v
    clean = re.sub(r'\s*\(.*?\)\s*$', '', name)
    clean = re.sub(r'\s*(Shop|Official|Store|US|USA)\s*$', '', clean, flags=re.IGNORECASE).strip()
    clean = re.sub(r'\s*(DO NOT|DONT|no more|No Longer).*$', '', clean, flags=re.IGNORECASE).strip()
    if not clean: clean = name
    bm[name] = clean
    return clean

MO_MAP = {'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
           'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
           'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

@st.cache_data
def parse_gmv_csv(file_bytes):
    text = file_bytes.decode('utf-8-sig')
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    header_idx = None
    for i, r in enumerate(rows):
        if r and str(r[0]).strip().upper() == 'BRAND':
            header_idx = i; break
    if header_idx is None: return None
    headers = rows[header_idx]
    month_cols = {}
    for ci, h in enumerate(headers):
        hl = str(h).strip().lower()
        for mname, mnum in MO_MAP.items():
            if mname in hl:
                for y in ['2026','2025','2024']:
                    if y in hl:
                        month_cols[(int(y), mnum)] = ci; break
                break
    data = []
    for r in rows[header_idx+1:]:
        if not r or not r[0] or r[0].strip() in ('Total',''): continue
        brand = r[0].strip()
        ps = r[1].strip() if len(r)>1 else ''
        status = r[3].strip() if len(r)>3 else ''
        monthly = {}
        for (year,month),ci in month_cols.items():
            if ci < len(r): monthly[(year,month)] = sf(r[ci])
        data.append({'brand':brand,'ps':ps,'status':status,'monthly':monthly})
    return data

@st.cache_data
def parse_broadway(file_bytes):
    import openpyxl
    wb = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    pr,vr,ct = [],[],[]
    if 'Partner Raw' in wb.sheetnames:
        for i,row in enumerate(wb['Partner Raw'].iter_rows(values_only=True)):
            if i==0: continue
            v=list(row)
            if not v[0]: continue
            pr.append({'shop':str(v[0]),'gmv':sf(v[1]),
                'impressions':sf(v[13]) if len(v)>13 else 0,
                'visitors':sf(v[14]) if len(v)>14 else 0,
                'affiliate_gmv':sf(v[10]) if len(v)>10 else 0,
                'month':int(sf(v[18])) if len(v)>18 and v[18] else 0,
                'year':int(sf(v[20])) if len(v)>20 and v[20] else 0})
    if 'Partner Video Raw' in wb.sheetnames:
        for i,row in enumerate(wb['Partner Video Raw'].iter_rows(values_only=True)):
            if i==0: continue
            v=list(row)
            if not v[0]: continue
            vr.append({'shop':str(v[0]),
                'videos':sf(v[10]) if len(v)>10 else 0,
                'lives':sf(v[9]) if len(v)>9 else 0,
                'month':int(sf(v[13])) if len(v)>13 and v[13] else 0,
                'year':int(sf(v[15])) if len(v)>15 and v[15] else 0})
    if 'Retainer Creator TAP Data' in wb.sheetnames:
        for i,row in enumerate(wb['Retainer Creator TAP Data'].iter_rows(values_only=True)):
            if i==0: continue
            v=list(row)
            if not v[0]: continue
            ct.append({'creator':str(v[5]) if len(v)>5 and v[5] else '',
                'shop':str(v[10]) if len(v)>10 and v[10] else '',
                'views':sf(v[18]) if len(v)>18 else 0,
                'likes':sf(v[19]) if len(v)>19 else 0,
                'month':int(sf(v[24])) if len(v)>24 and v[24] else 0,
                'year':int(sf(v[26])) if len(v)>26 and v[26] else 0})
    wb.close()
    return {'pr':pr,'vr':vr,'ct':ct}

@st.cache_data
def parse_amazon(file_bytes):
    import openpyxl
    wb = openpyxl.load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    target = None
    for s in wb.sheetnames:
        ws = wb[s]
        first = [str(c).lower() if c else '' for c in next(ws.iter_rows(max_row=1, values_only=True))]
        if any('start' in f and 'date' in f for f in first) and any('brand' in f for f in first):
            target = s; break
    if not target: wb.close(); return None
    ws = wb[target]; headers = None; rows = []
    for i,row in enumerate(ws.iter_rows(values_only=True)):
        v=list(row)
        if i==0: headers=[str(c).strip() if c else '' for c in v]; continue
        if v[0]: rows.append(v)
    wb.close()
    if not headers or not rows: return None
    hl=[h.lower() for h in headers]
    def fc(kws):
        for k in kws:
            for j,h in enumerate(hl):
                if all(w in h for w in k.split()):return j
        return None
    cs=fc(['start date']);cb=fc(['brand']);ct=fc(['total sales $','total sales'])
    cas=fc(['ad sales','advertising sales','sponsored sales'])
    cpv=fc(['total page view','page view'])
    if cs is None or cb is None or ct is None: return None
    data=[]
    for v in rows:
        try:
            s=v[cs]
            if isinstance(s,str):s=datetime.strptime(s.split(' ')[0],'%Y-%m-%d')
            elif not isinstance(s,datetime):continue
            sales=sf(v[ct]);ad_s=sf(v[cas]) if cas is not None else 0
            data.append({'year':s.year,'month':s.month,'brand_raw':str(v[cb]).strip(),
                'sales':sales,'ad_sales':ad_s,'organic':sales-ad_s,
                'page_views':sf(v[cpv]) if cpv is not None else 0})
        except:continue
    return data

def build_model(gmv_data, broadway, amazon_data, bm, cap_mult=4):
    tts_monthly = defaultdict(lambda: defaultdict(float))
    tts_meta = {}
    if gmv_data:
        for row in gmv_data:
            brand = norm(row['brand'], bm)
            if not brand: continue
            tts_meta[brand] = {'ps':row['ps'],'status':row['status']}
            for (y,m),gmv in row['monthly'].items():
                tts_monthly[brand][(y,m)] += gmv

    content = defaultdict(lambda: defaultdict(lambda:{'gmv':0,'impressions':0,'visitors':0,'affiliate_gmv':0,'videos':0,'lives':0,'views':0,'likes':0,'creators':set()}))
    if broadway:
        for p in broadway['pr']:
            if p['year']<2025:continue
            brand=norm(p['shop'],bm)
            if not brand:continue
            d=content[brand][(p['year'],p['month'])]
            d['gmv']+=p['gmv'];d['impressions']+=p['impressions'];d['visitors']+=p['visitors'];d['affiliate_gmv']+=p['affiliate_gmv']
        for v in broadway['vr']:
            if v['year']<2025:continue
            brand=norm(v['shop'],bm)
            if not brand:continue
            content[brand][(v['year'],v['month'])]['videos']+=v['videos']
            content[brand][(v['year'],v['month'])]['lives']+=v['lives']
        for c in broadway['ct']:
            if c['year']<2025:continue
            brand=norm(c['shop'],bm)
            if not brand:continue
            content[brand][(c['year'],c['month'])]['views']+=c['views']
            content[brand][(c['year'],c['month'])]['likes']+=c['likes']
            if c['creator']:content[brand][(c['year'],c['month'])]['creators'].add(c['creator'])

    amz_monthly = defaultdict(lambda: defaultdict(lambda:{'sales':0,'ad_sales':0,'organic':0,'page_views':0}))
    if amazon_data:
        for a in amazon_data:
            brand=norm(a['brand_raw'],bm)
            if not brand:continue
            d=amz_monthly[brand][(a['year'],a['month'])]
            d['sales']+=a['sales'];d['ad_sales']+=a['ad_sales'];d['organic']+=a['organic'];d['page_views']+=a['page_views']

    content_months = set()
    for brand,months in content.items():
        for k in months: content_months.add(k)
    latest = max(content_months) if content_months else (2026,1)

    all_brands = set(tts_monthly.keys()) | set(content.keys())
    if amazon_data: all_brands |= set(amz_monthly.keys())

    brands = []
    for brand in sorted(all_brands):
        tts_2025=[tts_monthly[brand].get((2025,m),0) for m in range(1,13)]
        amz_2025=[amz_monthly[brand].get((2025,m),{}).get('sales',0) for m in range(1,13)]
        org_2025=[amz_monthly[brand].get((2025,m),{}).get('organic',0) for m in range(1,13)]
        active=sum(1 for v in tts_2025 if v>0)
        has_amz=any(v>0 for v in amz_2025)
        lc=content[brand].get(latest,{})
        imp=lc.get('impressions',0) if isinstance(lc,dict) else 0
        vis=lc.get('visitors',0) if isinstance(lc,dict) else 0
        vid=lc.get('videos',0) if isinstance(lc,dict) else 0
        liv=lc.get('lives',0) if isinstance(lc,dict) else 0
        cre=len(lc.get('creators',set())) if isinstance(lc,dict) and isinstance(lc.get('creators'),set) else 0
        aff=lc.get('affiliate_gmv',0) if isinstance(lc,dict) else 0
        vviews=lc.get('views',0) if isinstance(lc,dict) else 0
        jan_tts=tts_monthly[brand].get(latest,0)
        if jan_tts==0: jan_tts=lc.get('gmv',0) if isinstance(lc,dict) else 0
        jan_amz=amz_monthly[brand].get(latest,{}).get('sales',0)

        r_best=0;r_type='same';conf='INSUF';rate=0.03;attributed=0;capped=False
        if has_amz and active>=3:
            ta=np.array(tts_2025,dtype=float);aa=np.array(amz_2025,dtype=float);oa=np.array(org_2025,dtype=float)
            cors=[]
            if np.std(ta)>0 and np.std(aa)>0:
                r,p=stats.pearsonr(ta,aa);cors.append((abs(r),r,'same'))
            if np.std(ta)>0 and np.std(oa)>0:
                r,p=stats.pearsonr(ta,oa);cors.append((abs(r),r,'org-same'))
            if len(ta)>3 and np.std(ta[:-1])>0 and np.std(aa[1:])>0:
                r,p=stats.pearsonr(ta[:-1],aa[1:]);cors.append((abs(r),r,'lag+1'))
            if len(ta)>3 and np.std(ta[:-1])>0 and np.std(oa[1:])>0:
                r,p=stats.pearsonr(ta[:-1],oa[1:]);cors.append((abs(r),r,'org-lag'))
            if cors:
                best=max(cors,key=lambda x:x[0]);r_best=best[1];r_type=best[2]
            if abs(r_best)>=0.8:conf='HIGH';rate=0.17
            elif abs(r_best)>=0.5:conf='MED';rate=0.12
            elif abs(r_best)>=0.3:conf='LOW';rate=0.06
            else:conf='WEAK';rate=0.02
            if jan_tts>0 and jan_amz>0:
                uc=jan_amz*rate;cp=jan_tts*cap_mult;attributed=min(uc,cp);capped=uc>cp
        elif active<3:conf='INSUF';rate=0.03
        else:conf='WEAK';rate=0.02

        meta=tts_meta.get(brand,{})
        if jan_tts==0 and jan_amz==0 and imp==0 and active==0 and sum(tts_2025)==0:continue
        brands.append({'brand':brand,'ps':meta.get('ps',''),'status':meta.get('status',''),
            'jan_tts':jan_tts,'jan_amz':jan_amz,'r_best':r_best,'r_type':r_type,'rate':rate,
            'confidence':conf,'attributed':attributed,'capped':capped,'active_months':active,
            'has_amz':has_amz,'impressions':imp,'visitors':vis,'videos':vid,'live_streams':liv,
            'creators':cre,'affiliate_gmv':aff,'video_views':vviews,
            'tts_2025':tts_2025,'amz_2025':amz_2025,'org_2025':org_2025,'tts_total':sum(tts_2025)})
    return brands, latest

# ═══════════════ HEADER ═══════════════
st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"><div style="width:7px;height:7px;border-radius:50%;background:{RED};box-shadow:0 0 12px rgba(255,59,82,.25);"></div><span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.16em;">Pattern x NextWave</span></div>',unsafe_allow_html=True)
st.markdown("# TTS to Amazon Lift Model")
sec("Upload Monthly Data")
c1,c2,c3=st.columns(3)
with c1:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'DM Sans\',sans-serif;color:{T1};">Monthly GMV</span><br><span style="font-size:10px;color:{T2};">TTS history 2024-2026 (.csv)</span></div>',unsafe_allow_html=True)
    gmv_file=st.file_uploader("gmv",type=['csv'],label_visibility="collapsed",key="gmv")
with c2:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'DM Sans\',sans-serif;color:{T1};">Broadway Tool</span><br><span style="font-size:10px;color:{T2};">Content metrics (.xlsm)</span></div>',unsafe_allow_html=True)
    bw_file=st.file_uploader("bw",type=['xlsm','xlsx'],label_visibility="collapsed",key="bw")
with c3:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'DM Sans\',sans-serif;color:{T1};">Amazon Report</span><br><span style="font-size:10px;color:{T2};">Monthly sales (.xlsx)</span></div>',unsafe_allow_html=True)
    amz_file=st.file_uploader("amz",type=['xlsx'],label_visibility="collapsed",key="amz")

if not gmv_file and not bw_file:
    st.markdown("---")
    st.info("Upload the **Monthly GMV** CSV to get started. Add **Broadway Tool** for content and **Amazon Report** for correlation.")
    st.markdown("""
**Three data sources:**
1. **Monthly GMV CSV** - TTS GMV by brand monthly (Jan 2025 to present). Core history for correlation.
2. **Broadway Tool** (.xlsm) - Content: impressions, visitors, videos, LIVE streams, creators.
3. **Amazon Report** (.xlsx) - Amazon sales by brand monthly. Enables correlation and attribution.
    """)
    st.stop()

gmv_data=None;broadway=None;amazon_data=None
bm=dict(BRAND_MAP)
if gmv_file: gmv_data=parse_gmv_csv(gmv_file.read());gmv_file.seek(0)
if bw_file: broadway=parse_broadway(bw_file.read());bw_file.seek(0)
if amz_file: amazon_data=parse_amazon(amz_file.read());amz_file.seek(0)

brands,latest=build_model(gmv_data,broadway,amazon_data,bm)
if not brands: st.error("No brand data found. Check file formats.");st.stop()
df=pd.DataFrame(brands).sort_values('jan_tts',ascending=False)
ml=f"{MO[latest[1]-1]} {latest[0]}"

allb=sorted(df['brand'].unique())
known=set(BRAND_MAP.values())
newb=[b for b in allb if b not in known]
st.markdown(f'<div style="margin:10px 0 4px;font:700 11px \'DM Sans\',sans-serif;color:{T2};">{len(allb)} brands detected from data | {ml}{f" | <span style=color:{YEL}>{len(newb)} new auto-added</span>" if newb else ""}</div>',unsafe_allow_html=True)

with st.expander(f"View all {len(allb)} brands",expanded=False):
    tags="".join(f'<span class="btag{"-new" if b in newb else ""}">{b}</span>' for b in allb)
    st.markdown(tags,unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f'<span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.16em;">Settings</span>',unsafe_allow_html=True)
    cap_mult=st.slider("GMV Cap Multiplier",2,8,4)
    st.caption(f"{ml} | {len(allb)} brands")
    st.markdown(f"**GMV CSV:** {'loaded' if gmv_data else 'none'}")
    st.markdown(f"**Broadway:** {'loaded' if broadway else 'none'}")
    st.markdown(f"**Amazon:** {'loaded' if amazon_data else 'none'}")

if cap_mult!=4:
    brands,latest=build_model(gmv_data,broadway,amazon_data,bm,cap_mult)
    df=pd.DataFrame(brands).sort_values('jan_tts',ascending=False)

# KPIs
ttts=df['jan_tts'].sum();tamz=df['jan_amz'].sum();tattr=df['attributed'].sum()
timp=df['impressions'].sum();tvis=df['visitors'].sum()
has_attribution=amazon_data is not None and tattr>0

cols=st.columns(5 if has_attribution else 4)
with cols[0]:st.markdown(kpi_html("TTS GMV",fd(ttts),ml),unsafe_allow_html=True)
ci=1
if has_attribution:
    with cols[ci]:
        blended=tattr/tamz*100 if tamz>0 else 0
        st.markdown(kpi_html("Attributed AMZ",fd(tattr),f"{blended:.2f}% of {fd(tamz)}",g=True),unsafe_allow_html=True)
    ci+=1
with cols[ci]:st.markdown(kpi_html("Impressions",fn(timp),"Broadway" if broadway else ""),unsafe_allow_html=True)
with cols[ci+1]:st.markdown(kpi_html("Visitors",fn(tvis),f"{tvis/timp*100:.2f}% rate" if timp>0 else ""),unsafe_allow_html=True)
with cols[ci+2]:
    lift=tattr/ttts if ttts>0 and has_attribution else 0
    st.markdown(kpi_html("Lift per TTS $1",f"${lift:.2f}" if has_attribution else "N/A","AMZ attributed / TTS GMV" if has_attribution else "Upload Amazon data"),unsafe_allow_html=True)

# ═══════════════ TABS ═══════════════
tl=["TTS Performance"]
if broadway:tl.append("Content Funnel")
if has_attribution:tl+=["Attribution","Correlation"]
tl.append("Deep Dive")
tabs=st.tabs(tl);ti=0

# TAB: TTS Performance
with tabs[ti]:
    ti+=1;sec(f"TTS Performance - {ml}")
    pf=df.copy()
    disp=pf[['brand','ps','status','jan_tts','tts_total','active_months']].copy()
    disp.columns=['Brand','Type','Status',f'GMV ({ml})','2025 Total','Active Mo.']
    st.dataframe(disp.sort_values(f'GMV ({ml})',ascending=False).style.format({f'GMV ({ml})':'${:,.0f}','2025 Total':'${:,.0f}'}),use_container_width=True,height=500)
    sec("Monthly TTS GMV Trend (2025) - Top 8")
    t8=pf.nlargest(8,'jan_tts')
    clrs=[RED,BLU,GRN,YEL,PUR,'#FF8C42','#4DE5FF','#FF6B9D']
    fig=go.Figure()
    for i,(_,b) in enumerate(t8.iterrows()):
        fig.add_trace(go.Scatter(x=MO,y=b['tts_2025'],name=b['brand'],line=dict(color=clrs[i%len(clrs)],width=2),marker=dict(size=4)))
    fig.update_yaxes(tickprefix='$',tickformat=',.0s')
    st.plotly_chart(pthem(fig,380),use_container_width=True)

# TAB: Content Funnel
if broadway:
    with tabs[ti]:
        ti+=1;sec(f"TTS Content Funnel - {ml}")
        fu=df[df['impressions']>0].copy()
        fu['visit_pct']=np.where(fu['impressions']>0,(fu['visitors']/fu['impressions']*100).round(2),0)
        fu['conv_pct']=np.where(fu['visitors']>0,(fu['jan_tts']/fu['visitors']*100).round(1),0)
        disp=fu[['brand','impressions','visitors','visit_pct','videos','live_streams','creators','jan_tts','conv_pct']].copy()
        disp.columns=['Brand','Impressions','Visitors','Visit %','Videos','Lives','Creators','TTS GMV','Conv %']
        st.dataframe(disp.sort_values('Impressions',ascending=False).style.format({'Impressions':'{:,.0f}','Visitors':'{:,.0f}','Visit %':'{:.2f}%','Videos':'{:,.0f}','Lives':'{:,.0f}','TTS GMV':'${:,.0f}','Conv %':'{:.1f}%'}),use_container_width=True,height=500)
        sec("Impressions vs TTS GMV")
        ch=fu.sort_values('impressions',ascending=True).tail(15)
        fig=make_subplots(specs=[[{"secondary_y":True}]])
        fig.add_trace(go.Bar(x=ch['impressions'],y=ch['brand'],orientation='h',name='Impressions',marker=dict(color=PUR,opacity=.35)),secondary_y=False)
        fig.add_trace(go.Bar(x=ch['jan_tts'],y=ch['brand'],orientation='h',name='TTS GMV',marker=dict(color=RED,opacity=.75)),secondary_y=True)
        fig.update_layout(barmode='overlay')
        st.plotly_chart(pthem(fig,max(300,len(ch)*28)),use_container_width=True)

# TAB: Attribution
if has_attribution:
    with tabs[ti]:
        ti+=1;sec("Attribution Model")
        c1,c2,c3=st.columns(3)
        with c1:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{BLU};margin-bottom:6px;">Correlation Rate</div><div style="font-size:11px;color:{T2};line-height:1.7;">r>=0.8: 17% | r>=0.5: 12% | r>=0.3: 6% | else: 2%</div></div>',unsafe_allow_html=True)
        with c2:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{YEL};margin-bottom:6px;">{cap_mult}x GMV Cap</div><div style="font-size:11px;color:{T2};line-height:1.7;">Attributed <= TTS GMV x {cap_mult}. If TTS=$0, attr=$0.</div></div>',unsafe_allow_html=True)
        with c3:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{GRN};margin-bottom:6px;">Confidence</div><div style="font-size:11px;color:{T2};line-height:1.7;">HIGH (r>=0.8) | MED (r>=0.5) | LOW (r>=0.3) | WEAK | INSUF</div></div>',unsafe_allow_html=True)
        sec("Brand Scorecard")
        ad=df[df['has_amz']].copy()
        ad['rate_pct']=(ad['rate']*100).round(0).astype(int).astype(str)+'%'
        ad['cap_f']=ad['capped'].apply(lambda x:'YES' if x else '-')
        disp=ad[['brand','confidence','r_best','r_type','rate_pct','jan_tts','jan_amz','attributed','cap_f']].copy()
        disp.columns=['Brand','Conf','r','Lag','Rate','TTS GMV','AMZ Sales','Attributed','Capped']
        st.dataframe(disp.sort_values('Attributed',ascending=False).style.format({'r':'{:.3f}','TTS GMV':'${:,.0f}','AMZ Sales':'${:,.0f}','Attributed':'${:,.0f}'}),use_container_width=True,height=500)
        sec("Attribution by Brand")
        af=ad[ad['attributed']>0].sort_values('attributed',ascending=True)
        fig=go.Figure(go.Bar(x=af['attributed'],y=af['brand'],orientation='h',marker=dict(color=[CC.get(c,T3) for c in af['confidence']],opacity=.8),text=[fd(v) for v in af['attributed']],textposition='outside',textfont=dict(size=10,family='JetBrains Mono',color=T1)))
        fig.update_xaxes(tickprefix='$',tickformat=',.0s')
        st.plotly_chart(pthem(fig,max(300,len(af)*28)),use_container_width=True)

# TAB: Correlation
if has_attribution:
    with tabs[ti]:
        ti+=1;sec("TTS vs Amazon Monthly (2025)")
        st.caption("Red bars = TTS GMV | Blue area = AMZ total | Green dashed = AMZ organic")
        cb=df[df['has_amz']&(df['active_months']>=3)].sort_values('r_best',ascending=False,key=abs)
        for _,b in cb.iterrows():
            conf_color=CC.get(b['confidence'],T3)
            cl1,cl2=st.columns([4,1])
            with cl1:st.markdown(f"**{b['brand']}** {badge_html(b['confidence'])} r = {b['r_best']:.3f} ({b['r_type']})",unsafe_allow_html=True)
            with cl2:st.markdown(f"<span style='font:700 12px JetBrains Mono;color:{conf_color};'>{fd(b['attributed'])} attributed</span>",unsafe_allow_html=True)
            fig=make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ',fill='tozeroy',fillcolor='rgba(77,166,255,.06)',line=dict(color=BLU,width=2),marker=dict(size=3)),secondary_y=False)
            fig.add_trace(go.Scatter(x=MO,y=b['org_2025'],name='Organic',line=dict(color=GRN,width=1.5,dash='dash')),secondary_y=False)
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS',marker=dict(color=RED,opacity=.75),width=.4),secondary_y=True)
            fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=False)
            fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=True)
            st.plotly_chart(pthem(fig,220),use_container_width=True)
            st.markdown("---")

# TAB: Deep Dive
with tabs[ti]:
    sec("Brand Deep Dive")
    sel=st.selectbox("Select Brand",df['brand'].tolist())
    if sel:
        b=df[df['brand']==sel].iloc[0]
        c1,c2=st.columns([3,2])
        with c1:
            st.markdown(f"#### {sel} Monthly (2025)")
            fig=go.Figure()
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS GMV',marker=dict(color=RED,opacity=.75)))
            if b['has_amz']:
                fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ Sales',yaxis='y2',line=dict(color=BLU,width=2),marker=dict(size=3)))
                fig.update_layout(yaxis2=dict(overlaying='y',side='right',gridcolor='rgba(0,0,0,0)',showline=False,tickprefix='$',tickformat=',.0s'))
            fig.update_yaxes(tickprefix='$',tickformat=',.0s')
            st.plotly_chart(pthem(fig,280),use_container_width=True)
        with c2:
            st.markdown(f"#### KPIs - {ml}")
            mets=[("TTS GMV",fd(b['jan_tts']),T1),("2025 Total",fd(b['tts_total']),T1),("Active Mo.",str(b['active_months']),T1),("Type",b['ps'] or '-',T2),("Impressions",fn(b['impressions']),PUR),("Visitors",fn(b['visitors']),T1),("Videos",fn(b['videos']),T1),("Lives",fn(b['live_streams']),T1),("Creators",str(b['creators']),YEL if b['creators'] else T3)]
            if b['has_amz']:mets+=[("","",BD),("AMZ Sales",fd(b['jan_amz']),BLU),("r",f"{b['r_best']:.3f}",CC.get(b['confidence'],T3)),("Confidence",b['confidence'],CC.get(b['confidence'],T3)),("Rate",f"{b['rate']*100:.0f}%",CC.get(b['confidence'],T3)),("Attributed",fd(b['attributed']),GRN),("Capped?","YES" if b['capped'] else "NO",YEL if b['capped'] else GRN)]
            for lb,vl,co in mets:
                if not lb:st.markdown(f"<div style='border-top:1px solid {BD};margin:6px 0;'></div>",unsafe_allow_html=True);continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid {BD};font:400 12px \'JetBrains Mono\',monospace;"><span style="color:{T2}">{lb}</span><span style="color:{co};font-weight:700">{vl}</span></div>',unsafe_allow_html=True)
        st.markdown("#### Monthly Detail (2025)")
        md=pd.DataFrame({'Month':MO,'TTS GMV':b['tts_2025']})
        fm={'TTS GMV':'${:,.0f}'}
        if b['has_amz']:md['AMZ Sales']=b['amz_2025'];md['AMZ Organic']=b['org_2025'];md['Ad Sales']=[a-o for a,o in zip(b['amz_2025'],b['org_2025'])];fm.update({'AMZ Sales':'${:,.0f}','AMZ Organic':'${:,.0f}','Ad Sales':'${:,.0f}'})
        st.dataframe(md.style.format(fm),use_container_width=True)

# ═══════════════ EXPORT ═══════════════
st.markdown("---");sec("Export")
ec=['brand','ps','jan_tts','tts_total','active_months','impressions','visitors','videos','live_streams','creators']
en=['Brand','Type',f'TTS GMV ({ml})','2025 Total','Active Mo.','Impressions','Visitors','Videos','Lives','Creators']
if has_attribution:ec+=['jan_amz','r_best','confidence','rate','attributed','capped'];en+=['AMZ Sales','r','Confidence','Rate','Attributed','Capped']
exp=df[ec].copy();exp.columns=en;csv_out=exp.to_csv(index=False)
st.download_button("Download Brand Summary (CSV)",csv_out,"tts_lift_summary.csv","text/csv")
st.caption(f"Pattern x NextWave | TTS Amazon Lift Model v4 | {ml} | {len(df)} brands")
