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

# ═══════════════ THEME — Pattern.com inspired ═══════════════
BG='#0A0A0A';S1='#111111';S2='#1A1A1A';BD='#2A2A2A'
# Pattern uses a dark black BG, white text, and coral/orange accent
CORAL='#FF6B35';GRN='#34D399';YEL='#FBBF24';BLU='#60A5FA'
PUR='#A78BFA';T1='#FFFFFF';T2='#9CA3AF';T3='#4B5563'
CC={'HIGH':GRN,'MED':YEL,'LOW':'#FB923C','WEAK':'#EF4444','INSUF':T3}
MO=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
.stApp{{background:{BG};}}
section[data-testid="stSidebar"]{{background:{S1};border-right:1px solid {BD};}}
h1,h2,h3{{font-family:'Inter',sans-serif!important;color:{T1}!important;font-weight:800!important;}}
.kpi{{background:{S1};border:1px solid {BD};border-radius:12px;padding:18px;text-align:center;position:relative;}}
.kpi .lb{{font:700 10px 'Inter',sans-serif;color:{T2};text-transform:uppercase;letter-spacing:.08em;}}
.kpi .vl{{font:800 28px 'Inter',sans-serif;color:{T1};letter-spacing:-.02em;margin:4px 0;}}
.kpi .vg{{font:800 28px 'Inter',sans-serif;color:{GRN};letter-spacing:-.02em;margin:4px 0;}}
.kpi .sb{{font:400 10px 'Inter',sans-serif;color:{T3};}}
.kpi .tip{{display:none;position:absolute;bottom:calc(100% + 8px);left:50%;transform:translateX(-50%);background:#1F2937;color:#D1D5DB;padding:8px 12px;border-radius:8px;font:400 11px 'Inter',sans-serif;white-space:normal;width:220px;text-align:left;z-index:99;box-shadow:0 4px 12px rgba(0,0,0,.4);line-height:1.4;}}
.kpi .tip::after{{content:'';position:absolute;top:100%;left:50%;transform:translateX(-50%);border:6px solid transparent;border-top-color:#1F2937;}}
.kpi:hover .tip{{display:block;}}
.stTabs [data-baseweb="tab-list"]{{gap:4px;}}
.stTabs [data-baseweb="tab"]{{background:transparent;border:1px solid {BD};border-radius:8px;padding:6px 16px;font-size:12px;font-weight:600;color:{T2};font-family:'Inter',sans-serif;}}
.stTabs [aria-selected="true"]{{background:rgba(255,107,53,.08)!important;border-color:{CORAL}!important;color:{CORAL}!important;}}
</style>""", unsafe_allow_html=True)

# ═══════════════ HELPERS ═══════════════
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
def kpi_h(lb,vl,sb="",g=False,tip=""):
    vc="vg" if g else "vl"
    tip_html = f'<div class="tip">{tip}</div>' if tip else ''
    return f'<div class="kpi">{tip_html}<div class="lb">{lb}</div><div class="{vc}">{vl}</div><div class="sb">{sb}</div></div>'
def sec(t):
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:28px 0 10px;"><div style="width:3px;height:16px;background:{CORAL};border-radius:2px;"></div><span style="font:700 10px \'Inter\',sans-serif;color:{CORAL};text-transform:uppercase;letter-spacing:.12em;">{t}</span></div>',unsafe_allow_html=True)
def badge_h(c):
    return f'<span style="display:inline-block;font:700 9px \'Inter\',sans-serif;padding:2px 8px;border-radius:4px;letter-spacing:.06em;background:{CC.get(c,T3)}15;color:{CC.get(c,T3)};">{c}</span>'
def pthem(fig,h=350):
    fig.update_layout(height=h,plot_bgcolor=BG,paper_bgcolor=BG,font=dict(family='Inter,sans-serif',color=T2,size=10),margin=dict(l=10,r=10,t=20,b=10),hovermode='x unified',legend=dict(orientation='h',y=-0.12,font=dict(size=10)))
    fig.update_xaxes(gridcolor=BD,showline=False);fig.update_yaxes(gridcolor=BD,showline=False)
    return fig

# ═══════════════ BRAND MAP ═══════════════
# All known name variants → canonical name
# Amazon report is the MASTER: only brands in Amazon report are included
BRAND_MAP={
    # Broadway shop → canonical
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
    # Amazon report → canonical
    'Atrium - Pure Encapsulations':'Pure Encapsulations','Dr Mercola':'Dr. Mercola',
    'Emerald Laboratories':'Emerald Labs','Herbs Etc.':'Herbs, Etc.',
    'Glanbia Performance Nutrition':'Optimum Nutrition',
    'Philips Avent':'Philips','Philips Norelco':'Philips','Philips Sonicare':'Philips',
    'Strider':'Strider Bikes','Youtheory':'YouTheory',
    # GMV CSV → canonical
    'Advocare':'AdvoCare','Tru Niagen':'Tru Niagen',
    'Vital Proteins':'Vital Proteins','Sakura':'Sakura',
    'Thorne Research':'Thorne Research','Pure Encapsulations':'Pure Encapsulations',
    'Hims & Hers':'Hims & Hers','YouTheory':'YouTheory',
    'SmartMouth':'SmartMouth','Strider Bikes':'Strider Bikes',
    'Dr. Mercola':'Dr. Mercola','Natural Factors':'Natural Factors',
    'Herbs, Etc.':'Herbs, Etc.','Emerald Labs':'Emerald Labs',
    'Balance of Nature':'Balance of Nature','AdvoCare':'AdvoCare',
    'Brownmed':'Brownmed','New Chapter':'New Chapter',
    'Optimum Nutrition':'Optimum Nutrition','Gaia':'Gaia',
    'Amazing Grass':'Amazing Grass','Philips':'Philips',
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

MO_MAP={'january':1,'february':2,'march':3,'april':4,'may':5,'june':6,
        'july':7,'august':8,'september':9,'october':10,'november':11,'december':12,
        'jan':1,'feb':2,'mar':3,'apr':4,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}

# ═══════════════ PARSERS ═══════════════

@st.cache_data
def parse_gmv_csv(fb):
    text=fb.decode('utf-8-sig');reader=csv.reader(io.StringIO(text));rows=list(reader)
    hi=None
    for i,r in enumerate(rows):
        if r and str(r[0]).strip().upper()=='BRAND': hi=i;break
    if hi is None: return None
    headers=rows[hi]; month_cols={}
    for ci,h in enumerate(headers):
        hl=str(h).strip().lower()
        for mn,mv in MO_MAP.items():
            if mn in hl:
                for y in ['2026','2025','2024']:
                    if y in hl: month_cols[(int(y),mv)]=ci;break
                break
    data=[]
    for r in rows[hi+1:]:
        if not r or not r[0] or r[0].strip() in ('Total',''): continue
        brand=r[0].strip();ps=r[1].strip() if len(r)>1 else '';status=r[3].strip() if len(r)>3 else ''
        monthly={}
        for (year,month),ci in month_cols.items():
            if ci<len(r): monthly[(year,month)]=sf(r[ci])
        data.append({'brand':brand,'ps':ps,'status':status,'monthly':monthly})
    return data

@st.cache_data
def parse_broadway(fb):
    import openpyxl
    wb=openpyxl.load_workbook(BytesIO(fb),read_only=True,data_only=True)
    pr,vr,ct=[],[],[]
    if 'Partner Raw' in wb.sheetnames:
        for i,row in enumerate(wb['Partner Raw'].iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            pr.append({'shop':str(v[0]),'gmv':sf(v[1]),
                'impressions':sf(v[13]) if len(v)>13 else 0,
                'visitors':sf(v[14]) if len(v)>14 else 0,
                'affiliate_gmv':sf(v[10]) if len(v)>10 else 0,
                'month':int(sf(v[18])) if len(v)>18 and v[18] else 0,
                'year':int(sf(v[20])) if len(v)>20 and v[20] else 0})
    if 'Partner Video Raw' in wb.sheetnames:
        for i,row in enumerate(wb['Partner Video Raw'].iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            vr.append({'shop':str(v[0]),
                'videos':sf(v[10]) if len(v)>10 else 0,
                'lives':sf(v[9]) if len(v)>9 else 0,
                'month':int(sf(v[13])) if len(v)>13 and v[13] else 0,
                'year':int(sf(v[15])) if len(v)>15 and v[15] else 0})
    if 'Retainer Creator TAP Data' in wb.sheetnames:
        for i,row in enumerate(wb['Retainer Creator TAP Data'].iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            ct.append({'creator':str(v[5]) if len(v)>5 and v[5] else '',
                'shop':str(v[10]) if len(v)>10 and v[10] else '',
                'views':sf(v[18]) if len(v)>18 else 0,
                'likes':sf(v[19]) if len(v)>19 else 0,
                'month':int(sf(v[24])) if len(v)>24 and v[24] else 0,
                'year':int(sf(v[26])) if len(v)>26 and v[26] else 0})
    wb.close()
    return {'pr':pr,'vr':vr,'ct':ct}

@st.cache_data
def parse_amazon(fb):
    import openpyxl
    wb=openpyxl.load_workbook(BytesIO(fb),read_only=True,data_only=True)
    target=None
    for s in wb.sheetnames:
        ws=wb[s]
        first=[str(c).lower() if c else '' for c in next(ws.iter_rows(max_row=1,values_only=True))]
        if any('start' in f and 'date' in f for f in first) and any('brand' in f for f in first):
            target=s;break
    if not target:wb.close();return None
    ws=wb[target];headers=None;rows=[]
    for i,row in enumerate(ws.iter_rows(values_only=True)):
        v=list(row)
        if i==0:headers=[str(c).strip() if c else '' for c in v];continue
        if v[0]:rows.append(v)
    wb.close()
    if not headers or not rows:return None
    hl=[h.lower() for h in headers]
    def fc(kws):
        for k in kws:
            for j,h in enumerate(hl):
                if all(w in h for w in k.split()):return j
        return None
    cs=fc(['start date']);cb=fc(['brand']);ct_col=fc(['total sales $','total sales'])
    cas=fc(['ad sales','advertising sales','sponsored sales'])
    cpv=fc(['total page view','page view'])
    if cs is None or cb is None or ct_col is None:return None
    data=[]
    for v in rows:
        try:
            s=v[cs]
            if isinstance(s,str):s=datetime.strptime(s.split(' ')[0],'%Y-%m-%d')
            elif not isinstance(s,datetime):continue
            sales=sf(v[ct_col]);ad_s=sf(v[cas]) if cas is not None else 0
            data.append({'year':s.year,'month':s.month,'brand_raw':str(v[cb]).strip(),
                'sales':sales,'ad_sales':ad_s,'organic':sales-ad_s,
                'page_views':sf(v[cpv]) if cpv is not None else 0})
        except:continue
    return data


# ═══════════════ MODEL BUILDER ═══════════════

def build_model(gmv_data, broadway, amazon_data, bm, cap_mult=4,
                browse_rate=0.15, recall_rate=0.002, amz_conv=0.10, amz_aov=35,
                report_month=None):
    """Build the full model. Amazon brands = master list."""

    # Step 1: Get Amazon master brand list
    amz_monthly = defaultdict(lambda: defaultdict(lambda:{'sales':0,'ad_sales':0,'organic':0,'page_views':0}))
    amz_brands = set()
    if amazon_data:
        for a in amazon_data:
            brand = norm(a['brand_raw'], bm)
            if not brand: continue
            amz_brands.add(brand)
            d = amz_monthly[brand][(a['year'], a['month'])]
            d['sales'] += a['sales']; d['ad_sales'] += a['ad_sales']
            d['organic'] += a['organic']; d['page_views'] += a['page_views']

    # Step 2: TTS monthly from GMV CSV
    tts_monthly = defaultdict(lambda: defaultdict(float))
    tts_meta = {}
    if gmv_data:
        for row in gmv_data:
            brand = norm(row['brand'], bm)
            if not brand: continue
            tts_meta[brand] = {'ps':row['ps'],'status':row['status']}
            for (y,m),gmv in row['monthly'].items():
                tts_monthly[brand][(y,m)] += gmv

    # Step 3: Content from Broadway
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

    # Use selected report month (or auto-detect)
    if report_month:
        latest = report_month
    else:
        content_months = set()
        for b,ms in content.items():
            for k in ms: content_months.add(k)
        latest = max(content_months) if content_months else (2026,1)

    # Step 4: Build brand models — ONLY for Amazon master brands
    master_brands = amz_brands if amz_brands else set(tts_monthly.keys())

    brands = []
    for brand in sorted(master_brands):
        tts_2025 = [tts_monthly[brand].get((2025,m),0) for m in range(1,13)]
        amz_2025 = [amz_monthly[brand].get((2025,m),{}).get('sales',0) for m in range(1,13)]
        org_2025 = [amz_monthly[brand].get((2025,m),{}).get('organic',0) for m in range(1,13)]
        active = sum(1 for v in tts_2025 if v > 0)

        # Latest month content
        lc = content[brand].get(latest,{})
        imp = lc.get('impressions',0) if isinstance(lc,dict) else 0
        vis = lc.get('visitors',0) if isinstance(lc,dict) else 0
        vid = lc.get('videos',0) if isinstance(lc,dict) else 0
        liv = lc.get('lives',0) if isinstance(lc,dict) else 0
        cre = len(lc.get('creators',set())) if isinstance(lc,dict) and isinstance(lc.get('creators'),set) else 0
        aff = lc.get('affiliate_gmv',0) if isinstance(lc,dict) else 0

        # Latest month TTS GMV
        jan_tts = tts_monthly[brand].get(latest,0)
        if jan_tts == 0: jan_tts = lc.get('gmv',0) if isinstance(lc,dict) else 0

        # Latest month AMZ
        jan_amz = amz_monthly[brand].get(latest,{}).get('sales',0)
        # If no latest month AMZ, use last available
        if jan_amz == 0:
            for m in range(12,0,-1):
                jan_amz = amz_monthly[brand].get((2025,m),{}).get('sales',0)
                if jan_amz > 0: break

        meta = tts_meta.get(brand,{})

        # ── CORRELATION MODEL ──
        r_best=0;r_type='same';conf='INSUF';corr_rate=0.03
        corr_attr=0;corr_capped=False
        if active >= 3 and any(v>0 for v in amz_2025):
            ta=np.array(tts_2025,dtype=float);aa=np.array(amz_2025,dtype=float);oa=np.array(org_2025,dtype=float)
            cors=[]
            if np.std(ta)>0 and np.std(aa)>0:
                r,p=stats.pearsonr(ta,aa);cors.append((abs(r),r,'same'))
            if np.std(ta)>0 and np.std(oa)>0:
                r,p=stats.pearsonr(ta,oa);cors.append((abs(r),r,'org-same'))
            if np.std(ta[:-1])>0 and np.std(aa[1:])>0:
                r,p=stats.pearsonr(ta[:-1],aa[1:]);cors.append((abs(r),r,'lag+1'))
            if np.std(ta[:-1])>0 and np.std(oa[1:])>0:
                r,p=stats.pearsonr(ta[:-1],oa[1:]);cors.append((abs(r),r,'org-lag'))
            if cors:
                best=max(cors,key=lambda x:x[0]);r_best=best[1];r_type=best[2]
            if abs(r_best)>=0.8:conf='HIGH';corr_rate=0.17
            elif abs(r_best)>=0.5:conf='MED';corr_rate=0.12
            elif abs(r_best)>=0.3:conf='LOW';corr_rate=0.06
            else:conf='WEAK';corr_rate=0.02
            if jan_tts>0 and jan_amz>0:
                uc=jan_amz*corr_rate;cp=jan_tts*cap_mult
                corr_attr=min(uc,cp);corr_capped=uc>cp
        elif active<3:conf='INSUF';corr_rate=0.03
        else:conf='WEAK';corr_rate=0.02

        # ── FUNNEL MODEL (dual-path) ──
        funnel_attr = 0
        path_a = 0  # non-buying visitors → Amazon
        path_b = 0  # impression-only → Amazon
        path_a_amz_vis = 0
        path_b_amz_vis = 0

        if vis > 0:
            tts_buyer_count = jan_tts / amz_aov if amz_aov > 0 else 0
            tts_buy_rate = min(tts_buyer_count / vis, 0.5) if vis > 0 else 0
            non_buyers = vis * (1 - tts_buy_rate)
            path_a_amz_vis = non_buyers * browse_rate
            path_a = path_a_amz_vis * amz_conv * amz_aov

        if imp > vis:
            view_only = imp - vis
            path_b_amz_vis = view_only * recall_rate
            path_b = path_b_amz_vis * amz_conv * amz_aov

        funnel_attr = path_a + path_b
        total_amz_vis = path_a_amz_vis + path_b_amz_vis

        brands.append({
            'brand':brand, 'ps':meta.get('ps',''), 'status':meta.get('status',''),
            'jan_tts':jan_tts, 'jan_amz':jan_amz, 'tts_total':sum(tts_2025),
            'active_months':active,
            # Correlation model
            'r_best':r_best, 'r_type':r_type, 'corr_rate':corr_rate,
            'confidence':conf, 'corr_attr':corr_attr, 'corr_capped':corr_capped,
            # Funnel model
            'funnel_attr':funnel_attr, 'path_a':path_a, 'path_b':path_b,
            'path_a_vis':path_a_amz_vis, 'path_b_vis':path_b_amz_vis,
            'total_amz_vis':total_amz_vis,
            # Content
            'impressions':imp, 'visitors':vis, 'videos':vid,
            'live_streams':liv, 'creators':cre, 'affiliate_gmv':aff,
            # Monthly series
            'tts_2025':tts_2025, 'amz_2025':amz_2025, 'org_2025':org_2025,
        })

    return brands, latest


# ═══════════════ APP LAYOUT ═══════════════

st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"><div style="width:7px;height:7px;border-radius:50%;background:{CORAL};box-shadow:0 0 12px rgba(255,107,53,.25);"></div><span style="font:700 10px \'Inter\',sans-serif;color:{CORAL};text-transform:uppercase;letter-spacing:.16em;">Pattern x NextWave</span></div>',unsafe_allow_html=True)
st.markdown("# TTS to Amazon Lift Model")

# ═══════════════ UPLOADS ═══════════════
sec("Upload Monthly Data")
c1,c2,c3 = st.columns(3)
with c1:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'Inter\',sans-serif;color:{T1};">Monthly GMV</span><br><span style="font-size:10px;color:{T2};">TTS history (.csv)</span></div>',unsafe_allow_html=True)
    gmv_file=st.file_uploader("gmv",type=['csv'],label_visibility="collapsed",key="gmv")
with c2:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'Inter\',sans-serif;color:{T1};">Broadway Tool</span><br><span style="font-size:10px;color:{T2};">Content metrics (.xlsm)</span></div>',unsafe_allow_html=True)
    bw_file=st.file_uploader("bw",type=['xlsm','xlsx'],label_visibility="collapsed",key="bw")
with c3:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 16px;text-align:center;"><span style="font:800 13px \'Inter\',sans-serif;color:{CORAL};">Amazon Report *</span><br><span style="font-size:10px;color:{T2};">Brand master + sales (.xlsx)</span></div>',unsafe_allow_html=True)
    amz_file=st.file_uploader("amz",type=['xlsx'],label_visibility="collapsed",key="amz")

if not amz_file:
    st.markdown("---")
    st.warning("The **Amazon Report** is required - it defines which brands are included (brands you sell on both TTS and Amazon). Upload it to continue.")
    st.markdown("""
**Three data sources:**
1. **Monthly GMV** (.csv) - TTS GMV by brand, monthly history. Needed for correlation.
2. **Broadway Tool** (.xlsm) - Content metrics: impressions, visitors, videos, creators. Needed for funnel model.
3. **Amazon Report** (.xlsx) - *Required.* Amazon sales by brand. Defines the brand master list.
    """)
    st.stop()

# Parse
bm = dict(BRAND_MAP)
gmv_data = parse_gmv_csv(gmv_file.read()) if gmv_file else None
if gmv_file: gmv_file.seek(0)
broadway = parse_broadway(bw_file.read()) if bw_file else None
if bw_file: bw_file.seek(0)
amazon_data = parse_amazon(amz_file.read())
amz_file.seek(0)

if not amazon_data:
    st.error("Could not parse Amazon report. Check the file has a 'Brands > Aggregations' sheet with Start Date and Brand columns.")
    st.stop()

# ═══════════════ MONTH SELECTOR ═══════════════
# Detect available months from Broadway data
avail_months = set()
if broadway:
    for p in broadway['pr']:
        if p['year'] >= 2025 and p['month'] > 0:
            avail_months.add((p['year'], p['month']))
if not avail_months and gmv_data:
    for row in gmv_data:
        for (y, m) in row['monthly']:
            if y >= 2025: avail_months.add((y, m))
if not avail_months:
    avail_months = {(2026, 1)}

sorted_months = sorted(avail_months, reverse=True)
month_options = [f"{MO[m-1]} {y}" for y, m in sorted_months]
month_tuples = sorted_months

sec("Select Reporting Month")
sel_month_label = st.selectbox("Analyze lift for:", month_options, index=0)
sel_month_idx = month_options.index(sel_month_label)
selected_month = month_tuples[sel_month_idx]
st.caption(f"All content, funnel, and attribution data below is for **{sel_month_label}** only.")

# ═══════════════ SIDEBAR SETTINGS ═══════════════
with st.sidebar:
    st.markdown(f'<span style="font:700 10px \'Inter\',sans-serif;color:{CORAL};text-transform:uppercase;letter-spacing:.16em;">Model Settings</span>',unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**Correlation Model**")
    cap_mult = st.slider("GMV Cap Multiplier", 2, 8, 4, help="Attributed <= TTS x this")
    st.markdown("---")
    st.markdown(f"**Funnel Model**")
    browse_rate = st.slider("Non-buyer Amazon browse %", 5, 40, 15, help="% of TTS visitors who didn't buy but later go to Amazon") / 100
    recall_rate = st.slider("Impression recall rate (per 1000)", 1, 10, 2, help="Per 1000 impression-only viewers who later search Amazon") / 1000
    amz_conv = st.slider("Amazon conversion %", 5, 20, 10) / 100
    amz_aov = st.slider("Amazon AOV ($)", 15, 75, 35)
    st.markdown("---")
    st.caption(f"GMV CSV: {'loaded' if gmv_data else 'none'}")
    st.caption(f"Broadway: {'loaded' if broadway else 'none'}")
    st.caption(f"Amazon: {len(amazon_data)} rows")

# Build model
brands, latest = build_model(gmv_data, broadway, amazon_data, bm,
    cap_mult=cap_mult, browse_rate=browse_rate, recall_rate=recall_rate,
    amz_conv=amz_conv, amz_aov=amz_aov, report_month=selected_month)

if not brands:
    st.error("No matching brands found. Check that brand names align across files.")
    st.stop()

df = pd.DataFrame(brands).sort_values('jan_tts', ascending=False)
ml = f"{MO[latest[1]-1]} {latest[0]}"

st.markdown(f'<div style="margin:10px 0;font:700 11px \'Inter\',sans-serif;color:{T2};">{len(df)} Amazon brands matched | Data: {ml}</div>',unsafe_allow_html=True)

# ═══════════════ KPIs ═══════════════
ttts=df['jan_tts'].sum(); tamz=df['jan_amz'].sum()
t_corr=df['corr_attr'].sum(); t_funnel=df['funnel_attr'].sum()
timp=df['impressions'].sum()

cols = st.columns(6)
with cols[0]: st.markdown(kpi_h("TTS GMV",fd(ttts),ml,tip="Total Gross Merchandise Value sold through TikTok Shop for the selected month across all Amazon-matched brands."),unsafe_allow_html=True)
with cols[1]: st.markdown(kpi_h("AMZ Sales",fd(tamz),"latest month",tip="Total Amazon sales revenue for the selected month across all matched brands. Sourced from the Amazon Broadway report."),unsafe_allow_html=True)
with cols[2]: st.markdown(kpi_h("Corr. Attributed",fd(t_corr),f"{t_corr/tamz*100:.2f}% of AMZ" if tamz>0 else "",g=True,tip="Amazon sales attributed to TikTok Shop activity using Pearson correlation between monthly TTS and AMZ trends. Higher correlation = higher attribution rate (17% for r≥0.8, down to 2% for weak). Capped at 4x TTS GMV."),unsafe_allow_html=True)
with cols[3]: st.markdown(kpi_h("Funnel Attributed",fd(t_funnel),f"{t_funnel/tamz*100:.2f}% of AMZ" if tamz>0 else "",g=True,tip="Amazon sales estimated via dual-path funnel: Path A = TTS visitors who didn't buy but later searched Amazon. Path B = viewers who saw TTS content and recalled the brand on Amazon. Uses configurable browse rate, recall rate, AMZ conversion, and AOV."),unsafe_allow_html=True)
with cols[4]: st.markdown(kpi_h("Impressions",fn(timp),"Broadway",tip="Total content impressions from the Broadway Tool for the selected month. Counts every time TTS content was shown to a viewer across all matched brands."),unsafe_allow_html=True)
with cols[5]:
    lift = t_corr/ttts if ttts>0 else 0
    st.markdown(kpi_h("Lift / TTS $1",f"${lift:.2f}","correlation model",tip="For every $1 of TTS GMV generated, this is how many dollars of Amazon sales are attributed via the correlation model. Higher = stronger halo effect from TikTok to Amazon."),unsafe_allow_html=True)


# ═══════════════ TABS ═══════════════
tabs = st.tabs(["Attribution","Funnel Model","Correlation","Content Funnel","Deep Dive"])

# TAB 1: ATTRIBUTION OVERVIEW
with tabs[0]:
    sec("Attribution Overview")
    st.caption("Two models side-by-side: correlation-based and funnel-based")
    ad = df.copy()
    ad['corr_rate_pct'] = (ad['corr_rate']*100).round(0).astype(int).astype(str)+'%'
    ad['cap_f'] = ad['corr_capped'].apply(lambda x:'YES' if x else '-')
    disp = ad[['brand','confidence','r_best','corr_rate_pct','corr_attr','funnel_attr','path_a','path_b','jan_tts','jan_amz','cap_f']].copy()
    disp.columns = ['Brand','Conf','r','Rate','Corr Attr','Funnel Attr','Funnel A (visitors)','Funnel B (impressions)','TTS GMV','AMZ Sales','Capped']
    st.dataframe(disp.sort_values('Corr Attr',ascending=False).style.format(
        {'r':'{:.3f}','Corr Attr':'${:,.0f}','Funnel Attr':'${:,.0f}',
         'Funnel A (visitors)':'${:,.0f}','Funnel B (impressions)':'${:,.0f}',
         'TTS GMV':'${:,.0f}','AMZ Sales':'${:,.0f}'}),
        use_container_width=True, height=550)

    sec("Attribution Comparison")
    cmp = df[['brand','corr_attr','funnel_attr']].copy()
    cmp = cmp[(cmp['corr_attr']>0)|(cmp['funnel_attr']>0)].sort_values('corr_attr',ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=cmp['brand'],x=cmp['corr_attr'],name='Correlation',orientation='h',marker=dict(color=GRN,opacity=.7)))
    fig.add_trace(go.Bar(y=cmp['brand'],x=cmp['funnel_attr'],name='Funnel',orientation='h',marker=dict(color=PUR,opacity=.7)))
    fig.update_layout(barmode='group')
    fig.update_xaxes(tickprefix='$',tickformat=',.0s')
    st.plotly_chart(pthem(fig,max(350,len(cmp)*30)),use_container_width=True)

# TAB 2: FUNNEL MODEL
with tabs[1]:
    sec("Dual-Path Funnel Model")
    st.markdown(f"""
**Path A — Non-Buying Visitors:**
TTS Visitors who didn't buy x **{browse_rate:.0%}** go to Amazon x **{amz_conv:.0%}** convert x **${amz_aov}** AOV

**Path B — Impression Recall:**
Impression-only viewers (saw content, didn't click) x **{recall_rate:.2%}** later search Amazon x **{amz_conv:.0%}** convert x **${amz_aov}** AOV

Adjust rates in the sidebar. Conservative defaults calibrated to match correlation model output.
    """)

    fu = df[['brand','impressions','visitors','jan_tts','path_a_vis','path_a','path_b_vis','path_b','total_amz_vis','funnel_attr']].copy()
    fu.columns = ['Brand','Impressions','TTS Visitors','TTS GMV','Path A AMZ Vis','Path A Sales','Path B AMZ Vis','Path B Sales','Total AMZ Vis','Funnel Attributed']
    st.dataframe(fu.sort_values('Funnel Attributed',ascending=False).style.format(
        {'Impressions':'{:,.0f}','TTS Visitors':'{:,.0f}','TTS GMV':'${:,.0f}',
         'Path A AMZ Vis':'{:,.0f}','Path A Sales':'${:,.0f}',
         'Path B AMZ Vis':'{:,.0f}','Path B Sales':'${:,.0f}',
         'Total AMZ Vis':'{:,.0f}','Funnel Attributed':'${:,.0f}'}),
        use_container_width=True, height=550)

    sec("Funnel Waterfall - Portfolio")
    total_vis = df['visitors'].sum()
    total_non_buy = total_vis - (ttts / amz_aov if amz_aov > 0 else 0)
    total_view_only = timp - total_vis
    total_a_vis = df['path_a_vis'].sum()
    total_b_vis = df['path_b_vis'].sum()
    total_amz_orders = t_funnel / amz_aov if amz_aov > 0 else 0

    funnel_labels = ['TTS Impressions','TTS Visitors','Non-Buyers','Path A: AMZ Visits','Path B: AMZ Visits','Est. AMZ Orders','Est. AMZ Sales']
    funnel_vals = [timp, total_vis, max(total_non_buy,0), total_a_vis, total_b_vis, total_amz_orders, t_funnel]
    funnel_colors = [PUR,BLU,YEL,GRN,GRN,CORAL,CORAL]
    fig = go.Figure(go.Bar(
        y=funnel_labels[::-1], x=funnel_vals[::-1], orientation='h',
        marker=dict(color=funnel_colors[::-1], opacity=.8),
        text=[fn(v) if i < 5 else fd(v) for i, v in enumerate(funnel_vals[::-1])],
        textposition='outside', textfont=dict(size=10, family='Inter', color=T1),
    ))
    st.plotly_chart(pthem(fig,400),use_container_width=True)

# TAB 3: CORRELATION
with tabs[2]:
    sec("Correlation Model - TTS vs Amazon Monthly (2025)")
    if not gmv_data:
        st.warning("Upload the **Monthly GMV CSV** to enable correlation analysis. It provides 2025 TTS history needed to correlate with Amazon sales.")
    else:
        st.caption("Red bars = TTS GMV | Blue area = AMZ total | Green dashed = AMZ organic")
        cb = df[df['active_months']>=3].sort_values('r_best',ascending=False,key=abs)
        if len(cb) == 0:
            st.info("No brands with 3+ active TTS months found. Correlation requires at least 3 months of TTS data.")
        for _,b in cb.iterrows():
            conf_color = CC.get(b['confidence'],T3)
            cl1,cl2 = st.columns([4,1])
            with cl1: st.markdown(f"**{b['brand']}** {badge_h(b['confidence'])} r = {b['r_best']:.3f} ({b['r_type']})",unsafe_allow_html=True)
            with cl2: st.markdown(f"<span style='font:700 12px Inter;color:{conf_color};'>{fd(b['corr_attr'])} attributed</span>",unsafe_allow_html=True)
            fig = make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ',fill='tozeroy',fillcolor='rgba(77,166,255,.06)',line=dict(color=BLU,width=2),marker=dict(size=3)),secondary_y=False)
            fig.add_trace(go.Scatter(x=MO,y=b['org_2025'],name='Organic',line=dict(color=GRN,width=1.5,dash='dash')),secondary_y=False)
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS',marker=dict(color=CORAL,opacity=.75),width=.4),secondary_y=True)
            fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=False)
            fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=True)
            st.plotly_chart(pthem(fig,220),use_container_width=True)
            st.markdown("---")

# TAB 4: CONTENT FUNNEL
with tabs[3]:
    sec(f"Content Funnel - {ml}")
    if not broadway:
        st.warning("Upload the **Broadway Tool** for content metrics.")
    else:
        fu2 = df[df['impressions']>0].copy()
        fu2['visit_pct'] = np.where(fu2['impressions']>0,(fu2['visitors']/fu2['impressions']*100).round(2),0)
        disp = fu2[['brand','impressions','visitors','visit_pct','videos','live_streams','creators','jan_tts']].copy()
        disp.columns = ['Brand','Impressions','Visitors','Visit %','Videos','Lives','Creators','TTS GMV']
        st.dataframe(disp.sort_values('Impressions',ascending=False).style.format(
            {'Impressions':'{:,.0f}','Visitors':'{:,.0f}','Visit %':'{:.2f}%',
             'Videos':'{:,.0f}','Lives':'{:,.0f}','TTS GMV':'${:,.0f}'}),
            use_container_width=True, height=500)

# TAB 5: DEEP DIVE
with tabs[4]:
    sec("Brand Deep Dive")
    sel = st.selectbox("Select Brand", df['brand'].tolist())
    if sel:
        b = df[df['brand']==sel].iloc[0]
        c1,c2 = st.columns([3,2])
        with c1:
            st.markdown(f"#### {sel} Monthly (2025)")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS GMV',marker=dict(color=CORAL,opacity=.75)))
            fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ Sales',yaxis='y2',line=dict(color=BLU,width=2),marker=dict(size=3)))
            fig.update_layout(yaxis2=dict(overlaying='y',side='right',gridcolor='rgba(0,0,0,0)',showline=False,tickprefix='$',tickformat=',.0s'))
            fig.update_yaxes(tickprefix='$',tickformat=',.0s')
            st.plotly_chart(pthem(fig,280),use_container_width=True)
        with c2:
            st.markdown(f"#### KPIs")
            conf_color = CC.get(b['confidence'],T3)
            mets = [
                ("TTS GMV",fd(b['jan_tts']),T1),("AMZ Sales",fd(b['jan_amz']),BLU),
                ("2025 TTS Total",fd(b['tts_total']),T1),("Active Mo.",str(b['active_months']),T1),
                ("","",BD),
                ("Correlation r",f"{b['r_best']:.3f}",conf_color),("Confidence",b['confidence'],conf_color),
                ("Corr Rate",f"{b['corr_rate']*100:.0f}%",conf_color),
                ("Corr Attributed",fd(b['corr_attr']),GRN),("Capped?","YES" if b['corr_capped'] else "NO",YEL if b['corr_capped'] else GRN),
                ("","",BD),
                ("Impressions",fn(b['impressions']),PUR),("Visitors",fn(b['visitors']),T1),
                ("Funnel Path A",fd(b['path_a']),GRN),("Funnel Path B",fd(b['path_b']),GRN),
                ("Funnel Attributed",fd(b['funnel_attr']),GRN),
                ("Est. AMZ Visitors",fn(b['total_amz_vis']),BLU),
            ]
            for lb,vl,co in mets:
                if not lb: st.markdown(f"<div style='border-top:1px solid {BD};margin:6px 0;'></div>",unsafe_allow_html=True);continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid {BD};font:400 12px \'Inter\',monospace;"><span style="color:{T2}">{lb}</span><span style="color:{co};font-weight:700">{vl}</span></div>',unsafe_allow_html=True)

        st.markdown("#### Monthly Detail (2025)")
        md = pd.DataFrame({'Month':MO,'TTS GMV':b['tts_2025'],'AMZ Sales':b['amz_2025'],'AMZ Organic':b['org_2025']})
        md['Ad Sales'] = [a-o for a,o in zip(b['amz_2025'],b['org_2025'])]
        st.dataframe(md.style.format({'TTS GMV':'${:,.0f}','AMZ Sales':'${:,.0f}','AMZ Organic':'${:,.0f}','Ad Sales':'${:,.0f}'}),use_container_width=True)

# ═══════════════ EXPORT ═══════════════
st.markdown("---"); sec("Export")
ec = df[['brand','ps','jan_tts','tts_total','jan_amz','active_months','r_best','confidence','corr_rate','corr_attr','corr_capped','impressions','visitors','funnel_attr','path_a','path_b']].copy()
ec.columns = ['Brand','Type',f'TTS GMV ({ml})','2025 TTS Total','AMZ Sales','Active Mo.','r','Confidence','Corr Rate','Corr Attributed','Capped','Impressions','Visitors','Funnel Attributed','Funnel Path A','Funnel Path B']
csv_out = ec.to_csv(index=False)
st.download_button("Download Attribution Summary (CSV)",csv_out,"tts_lift_attribution.csv","text/csv")
st.caption(f"Pattern x NextWave | TTS → Amazon Lift Model v5 | {ml} | {len(df)} brands")
