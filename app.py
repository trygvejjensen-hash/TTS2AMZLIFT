import streamlit as st
import pandas as pd
import numpy as np
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from collections import defaultdict
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="TTS → Amazon Lift Model", page_icon="📊", layout="wide")

BG='#07090E'; S1='#0D1017'; S2='#141820'; BD='#1C2030'
RED='#FF3B52'; GRN='#00E5A0'; YEL='#FFB020'; BLU='#4DA6FF'
PUR='#B07CFF'; T1='#E8EAF0'; T2='#7B8098'; T3='#3E4460'
CC={'HIGH':GRN,'MED':YEL,'LOW':'#FF8C42','WEAK':RED,'INSUF':T3}
MO=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=DM+Sans:wght@400;500;700;800&display=swap');
.stApp{{background:{BG};}} section[data-testid="stSidebar"]{{background:{S1};border-right:1px solid {BD};}}
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
div[data-testid="stDataFrame"]{{border:1px solid {BD};border-radius:10px;overflow:hidden;}}
</style>""", unsafe_allow_html=True)

def fd(v):
    if abs(v)>=1e6:return f"${v/1e6:.1f}M"
    if abs(v)>=1e3:return f"${v/1e3:.0f}K"
    return f"${v:,.0f}" if v else "$0"
def fn(v):
    if v>=1e6:return f"{v/1e6:.1f}M"
    if v>=1e3:return f"{v/1e3:.0f}K"
    return f"{v:,.0f}" if v else "0"
def sf(v):
    try:return float(str(v).replace('$','').replace(',',''))
    except:return 0.0
def kpi(lb,vl,sb="",g=False):
    vc="vg" if g else "vl"
    return f'<div class="kpi"><div class="lb">{lb}</div><div class="{vc}">{vl}</div><div class="sb">{sb}</div></div>'
def sec(t): st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin:28px 0 10px;"><div style="width:3px;height:16px;background:{RED};border-radius:2px;"></div><span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.12em;">{t}</span></div>',unsafe_allow_html=True)
def badge(c): return f'<span style="display:inline-block;font:800 9px \'JetBrains Mono\',monospace;padding:2px 8px;border-radius:3px;letter-spacing:.06em;background:{CC.get(c,T3)}15;color:{CC.get(c,T3)};">{c}</span>'
def pthem(fig,h=350):
    fig.update_layout(height=h,plot_bgcolor=BG,paper_bgcolor=BG,font=dict(family='JetBrains Mono,monospace',color=T2,size=10),margin=dict(l=10,r=10,t=20,b=10),hovermode='x unified',legend=dict(orientation='h',y=-0.12,font=dict(size=10)))
    fig.update_xaxes(gridcolor=BD,showline=False);fig.update_yaxes(gridcolor=BD,showline=False)
    return fig

BM={
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
    'MegaFood Shop':'MegaFood','Nutricost':'Nutricost','MuscleTech':'MuscleTech',
    'Babe Original':'Babe Original','Fanttik':'Fanttik','Fanttik Prime':'Fanttik','FanttikSolo':'Fanttik',
    'CeraVe':'CeraVe','Murad Skincare':'Murad','SuavecitoPomade':'Suavecito',
    'Snackworks':'Snackworks','OLLY Wellness':'OLLY','Zenwise Health':'Zenwise',
    'livehumann':'LiveHumann','Rocco & Roxie Supply Co.':'Rocco & Roxie',
    'Flora Health Shop':'Flora Health','Fazit':'Fazit','Tushbaby':'Tushbaby',
    'Urban Decay Cosmetics':'Urban Decay','urban decay':'Urban Decay',
    'Kradle':'Kradle','Lumineux':'Lumineux',"Renzo's Vitamins":"Renzo's",
    'Uqora Official':'Uqora','Isopure':'Isopure','Revolution Beauty':'Revolution Beauty',
    'Sloomoo Institute':'Sloomoo','Dr. Tobias':'Dr. Tobias','Buttermints':'Buttermints',
    'Perseek US':'Perseek','Zdeer Official':'Zdeer','ZdeerHealth':'Zdeer',
    'ArtNaturals Shop':'ArtNaturals','BLOOMCHICUSOFFICIAL':'BloomChic',
    'Timeless Skin Care':'Timeless Skin Care','byDash':'Dash',
    "K'lani":"K'lani",'Leatherman Tools':'Leatherman','PBfit':'PBfit',
    'Brutus Broth':'Brutus Broth','GET ONNIT':'Onnit','The Genius Brand Shop':'Genius Brand',
    'Integrative Therapeutics':'Integrative Therapeutics','Baby Brezza':'Baby Brezza',
    'Weider Global Nutrition':'Weider','CureHydration':'Cure Hydration',
    'G2G Bar':'G2G Bar','Quicksilver Scientific':'Quicksilver Scientific',
    'Life Extension Supplements':'Life Extension','Azzaro Parfums':'Azzaro','Azzaro':'Azzaro',
    'AriaMist':'AriaMist','Hoga Store':'Hoga','SIXSTAR PRO':'Six Star Pro',
    'HydraLyte':'HydraLyte','Humble Brands':'Humble Brands','K9 Feline Natural':'K9 Natural',
    'Shop at BeLive':'BeLive','Kiyomi Skin':'Kiyomi Skin','Elevate organic':'Elevate Organic',
    'Cosyuree.':'Cosyuree','Barimelts':'Barimelts','EZMelts':'EZMelts',
    'pattern.us':'Pattern',
    'Atrium - Pure Encapsulations':'Pure Encapsulations','Dr Mercola':'Dr. Mercola',
    'Emerald Laboratories':'Emerald Labs','Herbs Etc.':'Herbs, Etc.',
    'Glanbia Performance Nutrition':'Optimum Nutrition',
    'Philips Avent':'Philips','Philips Norelco':'Philips','Philips Sonicare':'Philips',
    'Strider':'Strider Bikes','Youtheory':'YouTheory',
}

def norm(name,bm):
    if not name or not str(name).strip():return None
    name=str(name).strip()
    if name in bm:return bm[name]
    for k,v in bm.items():
        if k.lower()==name.lower():return v
    clean=re.sub(r'\s*(Shop|Official|Store|US|USA)\s*$','',name,flags=re.IGNORECASE).strip()
    if not clean:clean=name
    bm[name]=clean
    return clean

@st.cache_data
def parse_bw(fb):
    import openpyxl
    wb=openpyxl.load_workbook(BytesIO(fb),read_only=True,data_only=True)
    pr,vr,ct=[],[],[]
    if 'Partner Raw' in wb.sheetnames:
        ws=wb['Partner Raw']
        for i,row in enumerate(ws.iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            pr.append({'shop':str(v[0]),'gmv':sf(v[1]),'items':sf(v[2]),'live_gmv':sf(v[3]),'video_gmv':sf(v[4]),'product_card_gmv':sf(v[5]),'ads_gmv':sf(v[6]),'ads_cost':sf(v[7]),'affiliate_gmv':sf(v[10]) if len(v)>10 else 0,'impressions':sf(v[13]) if len(v)>13 else 0,'visitors':sf(v[14]) if len(v)>14 else 0,'conv':sf(v[15]) if len(v)>15 else 0,'month':int(sf(v[18])) if len(v)>18 and v[18] else 0,'year':int(sf(v[20])) if len(v)>20 and v[20] else 0})
    if 'Partner Video Raw' in wb.sheetnames:
        ws=wb['Partner Video Raw']
        for i,row in enumerate(ws.iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            vr.append({'shop':str(v[0]),'shoppable_videos':sf(v[10]) if len(v)>10 else 0,'live_streams':sf(v[9]) if len(v)>9 else 0,'month':int(sf(v[13])) if len(v)>13 and v[13] else 0,'year':int(sf(v[15])) if len(v)>15 and v[15] else 0})
    if 'Retainer Creator TAP Data' in wb.sheetnames:
        ws=wb['Retainer Creator TAP Data']
        for i,row in enumerate(ws.iter_rows(values_only=True)):
            if i==0:continue
            v=list(row)
            if not v[0]:continue
            ct.append({'creator':str(v[5]) if len(v)>5 and v[5] else '','shop':str(v[10]) if len(v)>10 and v[10] else '','views':sf(v[18]) if len(v)>18 else 0,'likes':sf(v[19]) if len(v)>19 else 0,'gmv':sf(v[28]) if len(v)>28 else 0,'month':int(sf(v[24])) if len(v)>24 and v[24] else 0,'year':int(sf(v[26])) if len(v)>26 and v[26] else 0})
    wb.close()
    return {'pr':pr,'vr':vr,'ct':ct}

@st.cache_data
def parse_amz(fb):
    import openpyxl
    wb=openpyxl.load_workbook(BytesIO(fb),read_only=True,data_only=True)
    target=None
    for s in wb.sheetnames:
        ws=wb[s]
        first=[str(c).lower() if c else '' for c in next(ws.iter_rows(max_row=1,values_only=True))]
        if any('start' in f and 'date' in f for f in first) and any('brand' in f for f in first):
            target=s;break
    if not target:
        for s in wb.sheetnames:
            ws=wb[s]
            first=[str(c).lower() if c else '' for c in next(ws.iter_rows(max_row=1,values_only=True))]
            if len(first)>5 and any('brand' in f for f in first):
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
    def fc(kw):
        for k in kw:
            for j,h in enumerate(hl):
                if all(w in h for w in k.split()):return j
        return None
    cs=fc(['start date']);cb=fc(['brand']);ct=fc(['total sales $','total sales']);cpv=fc(['total page view','page view']);cas=fc(['ad sales','advertising sales','sponsored sales']);casp=fc(['ad spend','advertising spend','sponsored spend','total spend']);cu=fc(['total units','units sold','units']);co=fc(['total orders','orders'])
    if cs is None or cb is None or ct is None:return None
    data=[]
    for v in rows:
        try:
            s=v[cs]
            if isinstance(s,str):s=datetime.strptime(s.split(' ')[0],'%Y-%m-%d')
            elif not isinstance(s,datetime):continue
            brand=str(v[cb]).strip();sales=sf(v[ct]);ad_s=sf(v[cas]) if cas else 0
            data.append({'year':s.year,'month':s.month,'brand_raw':brand,'sales':sales,'ad_sales':ad_s,'organic':sales-ad_s,'page_views':sf(v[cpv]) if cpv else 0,'ad_spend':sf(v[casp]) if casp else 0,'units':sf(v[cu]) if cu else 0,'orders':sf(v[co]) if co else 0})
        except:continue
    return data

def build(bw,amz,bm,cap=4):
    tbm=defaultdict(lambda:defaultdict(lambda:{'gmv':0,'impressions':0,'visitors':0,'affiliate_gmv':0,'ads_cost':0,'items':0,'videos':0,'live_streams':0,'video_views':0,'video_likes':0,'creators':set()}))
    for p in bw['pr']:
        if p['year']<2025:continue
        b=norm(p['shop'],bm)
        if not b:continue
        k=(p['year'],p['month']);d=tbm[b][k]
        d['gmv']+=p['gmv'];d['impressions']+=p['impressions'];d['visitors']+=p['visitors'];d['affiliate_gmv']+=p['affiliate_gmv'];d['ads_cost']+=p['ads_cost'];d['items']+=p['items']
    for v in bw['vr']:
        if v['year']<2025:continue
        b=norm(v['shop'],bm)
        if not b:continue
        k=(v['year'],v['month']);tbm[b][k]['videos']+=v['shoppable_videos'];tbm[b][k]['live_streams']+=v['live_streams']
    for c in bw['ct']:
        if c['year']<2025:continue
        b=norm(c['shop'],bm)
        if not b:continue
        k=(c['year'],c['month']);tbm[b][k]['video_views']+=c['views'];tbm[b][k]['video_likes']+=c['likes']
        if c['creator']:tbm[b][k]['creators'].add(c['creator'])
    abm=defaultdict(lambda:defaultdict(lambda:{'sales':0,'ad_sales':0,'organic':0,'page_views':0,'ad_spend':0}))
    if amz:
        for a in amz:
            b=norm(a['brand_raw'],bm)
            if not b:continue
            k=(a['year'],a['month']);d=abm[b][k];d['sales']+=a['sales'];d['ad_sales']+=a['ad_sales'];d['organic']+=a['organic'];d['page_views']+=a['page_views'];d['ad_spend']+=a['ad_spend']
    am=set()
    for b,ms in tbm.items():
        for k in ms:am.add(k)
    lat=max(am) if am else (2026,1)
    ac=set(tbm.keys())
    if amz:ac|=set(abm.keys())
    brands=[]
    for brand in sorted(ac):
        tm=tbm.get(brand,{});azm=abm.get(brand,{})
        t25=[tm.get((2025,m),{}).get('gmv',0) for m in range(1,13)]
        a25=[azm.get((2025,m),{}).get('sales',0) for m in range(1,13)]
        o25=[azm.get((2025,m),{}).get('organic',0) for m in range(1,13)]
        act=sum(1 for v in t25 if v>0);ha=any(v>0 for v in a25)
        lm=tm.get(lat,{})
        jt=lm.get('gmv',0) if isinstance(lm,dict) else 0
        imp=lm.get('impressions',0) if isinstance(lm,dict) else 0
        vis=lm.get('visitors',0) if isinstance(lm,dict) else 0
        vid=lm.get('videos',0) if isinstance(lm,dict) else 0
        liv=lm.get('live_streams',0) if isinstance(lm,dict) else 0
        cre=len(lm.get('creators',set())) if isinstance(lm,dict) and isinstance(lm.get('creators'),set) else 0
        aff=lm.get('affiliate_gmv',0) if isinstance(lm,dict) else 0
        vv=lm.get('video_views',0) if isinstance(lm,dict) else 0
        alm=azm.get(lat,{});ja=alm.get('sales',0) if isinstance(alm,dict) else 0
        rb,rt,conf,rate=0,'same','INSUF',0.03;attr=0;capped=False
        if ha and act>=3:
            ta=np.array(t25,dtype=float);aa=np.array(a25,dtype=float);oa=np.array(o25,dtype=float)
            cors=[]
            if np.std(ta)>0 and np.std(aa)>0:r,p=stats.pearsonr(ta,aa);cors.append((abs(r),r,'same'))
            if np.std(ta)>0 and np.std(oa)>0:r,p=stats.pearsonr(ta,oa);cors.append((abs(r),r,'org-same'))
            if np.std(ta[:-1])>0 and np.std(aa[1:])>0:r,p=stats.pearsonr(ta[:-1],aa[1:]);cors.append((abs(r),r,'lag+1'))
            if np.std(ta[:-1])>0 and np.std(oa[1:])>0:r,p=stats.pearsonr(ta[:-1],oa[1:]);cors.append((abs(r),r,'org-lag'))
            if cors:best=max(cors,key=lambda x:x[0]);rb=best[1];rt=best[2]
            if act<3:conf='INSUF'
            elif abs(rb)>=0.8:conf='HIGH'
            elif abs(rb)>=0.5:conf='MED'
            elif abs(rb)>=0.3:conf='LOW'
            else:conf='WEAK'
            if abs(rb)>=0.8:rate=0.17
            elif abs(rb)>=0.5:rate=0.12
            elif abs(rb)>=0.3:rate=0.06
            elif conf=='INSUF':rate=0.03
            else:rate=0.02
            if jt>0 and ja>0:uc=ja*rate;cp=jt*cap;attr=min(uc,cp);capped=uc>cp
        elif act<3:conf='INSUF';rate=0.03
        else:conf='WEAK';rate=0.02
        if jt==0 and ja==0 and imp==0 and act==0:continue
        brands.append({'brand':brand,'jan_tts':jt,'jan_amz':ja,'r_best':rb,'r_type':rt,'rate':rate,'confidence':conf,'attributed':attr,'capped':capped,'active_months':act,'has_amz':ha,'impressions':imp,'visitors':vis,'videos':vid,'live_streams':liv,'creators':cre,'affiliate_gmv':aff,'video_views':vv,'tts_2025':t25,'amz_2025':a25,'org_2025':o25})
    return brands,lat

# ═══════════════ HEADER ═══════════════

st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"><div style="width:7px;height:7px;border-radius:50%;background:{RED};box-shadow:0 0 12px rgba(255,59,82,.25);"></div><span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.16em;">Pattern × NextWave</span></div>',unsafe_allow_html=True)
st.markdown("# TTS → Amazon Lift Model")

# ═══════════════ UPLOAD BUTTONS ═══════════════

sec("Upload Monthly Data")
c1,c2=st.columns(2)
with c1:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 20px;text-align:center;"><span style="font:800 13px \'DM Sans\',sans-serif;color:{T1};">📦 Broadway Tool</span><br><span style="font-size:11px;color:{T2};">TTS GMV · impressions · videos · creators</span></div>',unsafe_allow_html=True)
    bw_file=st.file_uploader("bw",type=['xlsm','xlsx'],label_visibility="collapsed",key="bw")
with c2:
    st.markdown(f'<div style="background:{S1};border:2px dashed {BD};border-radius:12px;padding:14px 20px;text-align:center;"><span style="font:800 13px \'DM Sans\',sans-serif;color:{T1};">📊 Amazon Report</span><br><span style="font-size:11px;color:{T2};">Monthly sales · ad spend · page views</span></div>',unsafe_allow_html=True)
    amz_file=st.file_uploader("amz",type=['xlsx'],label_visibility="collapsed",key="amz")

if not bw_file:
    st.markdown("---")
    st.info("👆 Upload the **Broadway Tool** to get started. Amazon Report is optional but enables correlation + attribution.")
    st.stop()

bw=parse_bw(bw_file.read());bw_file.seek(0)
amz=None
if amz_file:amz=parse_amz(amz_file.read());amz_file.seek(0)

bm=dict(BM)

with st.sidebar:
    st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><div style="width:7px;height:7px;border-radius:50%;background:{RED};"></div><span style="font:800 10px \'JetBrains Mono\',monospace;color:{RED};text-transform:uppercase;letter-spacing:.16em;">Settings</span></div>',unsafe_allow_html=True)
    cap=st.slider("GMV Cap Multiplier",2,8,4,help="Attributed AMZ ≤ TTS GMV × this")

brands,lat=build(bw,amz,bm,cap)
if not brands:st.error("No brand data found.");st.stop()

df=pd.DataFrame(brands).sort_values('jan_tts',ascending=False)
ml=f"{MO[lat[1]-1]} {lat[0]}"
allb=sorted(df['brand'].unique())
newb=[b for b in allb if b not in set(BM.values())]

st.markdown(f'<div style="margin:10px 0 4px;font:700 11px \'DM Sans\',sans-serif;color:{T2};">{len(allb)} brands detected · {ml}{f" · <span style=color:{YEL}>{len(newb)} new</span>" if newb else ""}</div>',unsafe_allow_html=True)
with st.expander(f"View all {len(allb)} brands",expanded=False):
    tags="".join(f'<span class="btag{"-new" if b in newb else ""}">{b}</span>' for b in allb)
    st.markdown(tags,unsafe_allow_html=True)
    if newb:st.caption("⚡ Yellow border = new brand auto-detected from your data")

with st.sidebar:
    st.caption(f"{ml} · {len(allb)} brands")
    st.markdown(f"**Broadway rows:** {len(bw['pr']):,}")
    if amz:st.markdown(f"**Amazon rows:** {len(amz):,}")
    else:st.markdown("**Amazon:** _not uploaded_")

# ═══════════════ KPIs ═══════════════

ttts=df['jan_tts'].sum();tamz=df['jan_amz'].sum();tattr=df['attributed'].sum()
timp=df['impressions'].sum();tvis=df['visitors'].sum();tvid=df['videos'].sum()

cols=st.columns(5 if amz else 4)
with cols[0]:st.markdown(kpi("TTS GMV",fd(ttts),ml),unsafe_allow_html=True)
ci=1
if amz:
    with cols[ci]:st.markdown(kpi("Attributed AMZ",fd(tattr),f"from {fd(tamz)} total",g=True),unsafe_allow_html=True)
    ci+=1
with cols[ci]:st.markdown(kpi("Impressions",fn(timp),"Broadway"),unsafe_allow_html=True)
with cols[ci+1]:st.markdown(kpi("Visitors",fn(tvis),f"{tvis/timp*100:.2f}% rate" if timp else ""),unsafe_allow_html=True)
with cols[ci+2]:st.markdown(kpi("Videos + Lives",fn(tvid+df['live_streams'].sum()),f"{len(df)} brands"),unsafe_allow_html=True)

# ═══════════════ TABS ═══════════════

tl=["📊 Content Funnel","📈 TTS Performance"]
if amz:tl+=["🔗 Attribution","📉 Correlation"]
tl.append("🔍 Deep Dive")
tabs=st.tabs(tl);ti=0

with tabs[ti]:
    ti+=1;sec(f"TTS Content Funnel — {ml}")
    fu=df[df['impressions']>0].copy()
    fu['visit_%']=np.where(fu['impressions']>0,(fu['visitors']/fu['impressions']*100).round(2),0)
    fu['conv_%']=np.where(fu['visitors']>0,(fu['jan_tts']/fu['visitors']*100).round(1),0)
    st.dataframe(fu[['brand','impressions','visitors','visit_%','videos','live_streams','creators','affiliate_gmv','jan_tts','conv_%']].rename(columns={'brand':'Brand','impressions':'Impressions','visitors':'Visitors','visit_%':'Visit %','videos':'Videos','live_streams':'Lives','creators':'Creators','affiliate_gmv':'Affiliate GMV','jan_tts':'TTS GMV','conv_%':'Conv %'}).sort_values('Impressions',ascending=False).style.format({'Impressions':'{:,.0f}','Visitors':'{:,.0f}','Visit %':'{:.2f}%','Videos':'{:,.0f}','Lives':'{:,.0f}','Affiliate GMV':'${:,.0f}','TTS GMV':'${:,.0f}','Conv %':'{:.1f}%'}).background_gradient(subset=['Impressions'],cmap='Purples',vmin=0).background_gradient(subset=['TTS GMV'],cmap='Reds',vmin=0),use_container_width=True,height=500)
    sec("Impressions vs TTS GMV")
    ch=fu.sort_values('impressions',ascending=True).tail(15)
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=ch['impressions'],y=ch['brand'],orientation='h',name='Impressions',marker=dict(color=PUR,opacity=.35)),secondary_y=False)
    fig.add_trace(go.Bar(x=ch['jan_tts'],y=ch['brand'],orientation='h',name='TTS GMV',marker=dict(color=RED,opacity=.75)),secondary_y=True)
    fig.update_layout(barmode='overlay');st.plotly_chart(pthem(fig,max(300,len(ch)*28)),use_container_width=True)

with tabs[ti]:
    ti+=1;sec(f"TTS Performance — {ml}")
    pf=df.copy();pf['tts_2025_total']=pf['tts_2025'].apply(sum)
    st.dataframe(pf[['brand','jan_tts','tts_2025_total','active_months','impressions','visitors','videos']].rename(columns={'brand':'Brand','jan_tts':f'GMV ({ml})','tts_2025_total':'2025 Total','active_months':'Active Mo.','impressions':'Impressions','visitors':'Visitors','videos':'Videos'}).sort_values(f'GMV ({ml})',ascending=False).style.format({f'GMV ({ml})':'${:,.0f}','2025 Total':'${:,.0f}','Impressions':'{:,.0f}','Visitors':'{:,.0f}','Videos':'{:,.0f}'}).background_gradient(subset=[f'GMV ({ml})'],cmap='Reds',vmin=0),use_container_width=True,height=500)
    sec("Monthly TTS GMV Trend (2025) — Top 8")
    t8=pf.nlargest(8,'jan_tts');cl=[RED,BLU,GRN,YEL,PUR,'#FF8C42','#4DE5FF','#FF6B9D']
    fig=go.Figure()
    for i,(_,b) in enumerate(t8.iterrows()):fig.add_trace(go.Scatter(x=MO,y=b['tts_2025'],name=b['brand'],line=dict(color=cl[i%len(cl)],width=2),marker=dict(size=4)))
    fig.update_yaxes(tickprefix='$',tickformat=',.0s');st.plotly_chart(pthem(fig,380),use_container_width=True)

if amz:
    with tabs[ti]:
        ti+=1;sec("Attribution Model")
        c1,c2,c3=st.columns(3)
        with c1:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{BLU};margin-bottom:6px;">① Correlation Rate</div><div style="font-size:11px;color:{T2};line-height:1.7;">Monthly TTS vs AMZ (Pearson r).<br>r≥0.8→17% · r≥0.5→12% · r≥0.3→6% · else 2%</div></div>',unsafe_allow_html=True)
        with c2:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{YEL};margin-bottom:6px;">② {cap}x GMV Cap</div><div style="font-size:11px;color:{T2};line-height:1.7;">Attributed ≤ TTS GMV × {cap}.<br>TTS=$0 → attr=$0.</div></div>',unsafe_allow_html=True)
        with c3:st.markdown(f'<div style="background:{S1};border:1px solid {BD};border-radius:10px;padding:14px;"><div style="font:800 11px \'JetBrains Mono\',monospace;color:{GRN};margin-bottom:6px;">③ Confidence</div><div style="font-size:11px;color:{T2};line-height:1.7;">HIGH (r≥0.8) · MED (r≥0.5) · LOW (r≥0.3) · WEAK · INSUF</div></div>',unsafe_allow_html=True)
        sec("Brand Scorecard")
        ad=df[df['has_amz']].copy();ad['rate_%']=(ad['rate']*100).round(0).astype(int).astype(str)+'%';ad['cap_f']=ad['capped'].apply(lambda x:'⚠️ YES' if x else '—')
        st.dataframe(ad[['brand','confidence','r_best','r_type','rate_%','jan_tts','impressions','jan_amz','attributed','cap_f']].rename(columns={'brand':'Brand','confidence':'Conf','r_best':'r','r_type':'Lag','rate_%':'Rate','jan_tts':'TTS GMV','impressions':'Impressions','jan_amz':'AMZ Sales','attributed':'Attributed','cap_f':'Capped'}).sort_values('Attributed',ascending=False).style.format({'r':'{:.3f}','TTS GMV':'${:,.0f}','Impressions':'{:,.0f}','AMZ Sales':'${:,.0f}','Attributed':'${:,.0f}'}).background_gradient(subset=['Attributed'],cmap='Greens',vmin=0),use_container_width=True,height=500)
        sec("Attribution by Brand")
        af=ad[ad['attributed']>0].sort_values('attributed',ascending=True)
        fig=go.Figure(go.Bar(x=af['attributed'],y=af['brand'],orientation='h',marker=dict(color=[CC.get(c,T3) for c in af['confidence']],opacity=.8),text=[fd(v) for v in af['attributed']],textposition='outside',textfont=dict(size=10,family='JetBrains Mono',color=T1)))
        fig.update_xaxes(tickprefix='$',tickformat=',.0s');st.plotly_chart(pthem(fig,max(300,len(af)*28)),use_container_width=True)

    with tabs[ti]:
        ti+=1;sec("TTS vs Amazon — Monthly (2025)")
        st.caption("Red = TTS GMV · Blue = AMZ total · Green dashed = AMZ organic")
        cb=df[df['has_amz']&(df['active_months']>=3)].sort_values('r_best',ascending=False,key=abs)
        for _,b in cb.iterrows():
            cl1,cl2=st.columns([4,1])
            with cl1:st.markdown(f"**{b['brand']}** {badge(b['confidence'])} — r = {b['r_best']:.3f} ({b['r_type']})",unsafe_allow_html=True)
            conf_col=CC.get(b['confidence'],T3)
            with cl2:st.markdown(f"<span style='font:700 12px JetBrains Mono;color:{conf_col};'>{fd(b['attributed'])} attributed</span>",unsafe_allow_html=True)
            fig=make_subplots(specs=[[{"secondary_y":True}]])
            fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ Sales',fill='tozeroy',fillcolor='rgba(77,166,255,.06)',line=dict(color=BLU,width=2),marker=dict(size=3,color=BLU)),secondary_y=False)
            fig.add_trace(go.Scatter(x=MO,y=b['org_2025'],name='AMZ Organic',line=dict(color=GRN,width=1.5,dash='dash')),secondary_y=False)
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS GMV',marker=dict(color=RED,opacity=.75),width=.4),secondary_y=True)
            fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=False);fig.update_yaxes(tickprefix='$',tickformat=',.0s',secondary_y=True)
            st.plotly_chart(pthem(fig,220),use_container_width=True);st.markdown("---")

with tabs[ti]:
    sec("Brand Deep Dive")
    sel=st.selectbox("Select Brand",df['brand'].tolist())
    if sel:
        b=df[df['brand']==sel].iloc[0]
        c1,c2=st.columns([3,2])
        with c1:
            st.markdown(f"#### {sel} — Monthly (2025)")
            fig=go.Figure()
            fig.add_trace(go.Bar(x=MO,y=b['tts_2025'],name='TTS GMV',marker=dict(color=RED,opacity=.75)))
            if b['has_amz']:
                fig.add_trace(go.Scatter(x=MO,y=b['amz_2025'],name='AMZ Sales',yaxis='y2',line=dict(color=BLU,width=2),marker=dict(size=3)))
                fig.update_layout(yaxis2=dict(overlaying='y',side='right',gridcolor='rgba(0,0,0,0)',showline=False,tickprefix='$',tickformat=',.0s'))
            fig.update_yaxes(tickprefix='$',tickformat=',.0s');st.plotly_chart(pthem(fig,280),use_container_width=True)
        with c2:
            st.markdown(f"#### KPIs — {ml}")
            mets=[("TTS GMV",fd(b['jan_tts']),T1),("2025 Total",fd(sum(b['tts_2025'])),T1),("Active Mo.",str(b['active_months']),T1),("Impressions",fn(b['impressions']),PUR),("Visitors",fn(b['visitors']),T1),("Videos",fn(b['videos']),T1),("Lives",fn(b['live_streams']),T1),("Creators",str(b['creators']),YEL if b['creators'] else T3),("Affiliate GMV",fd(b['affiliate_gmv']),T1)]
            if b['has_amz']:mets+=[("","",BD),("AMZ Sales",fd(b['jan_amz']),BLU),("r",f"{b['r_best']:.3f}" if b['r_best'] else '—',CC.get(b['confidence'],T3)),("Confidence",b['confidence'],CC.get(b['confidence'],T3)),("Rate",f"{b['rate']*100:.0f}%",CC.get(b['confidence'],T3)),("Attributed",fd(b['attributed']),GRN),("Capped?","YES" if b['capped'] else "NO",YEL if b['capped'] else GRN)]
            for lb,vl,co in mets:
                if not lb:st.markdown(f"<div style='border-top:1px solid {BD};margin:6px 0;'></div>",unsafe_allow_html=True);continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid {BD};font:400 12px \'JetBrains Mono\',monospace;"><span style="color:{T2}">{lb}</span><span style="color:{co};font-weight:700">{vl}</span></div>',unsafe_allow_html=True)
        st.markdown("#### Monthly Detail (2025)")
        md=pd.DataFrame({'Month':MO,'TTS GMV':b['tts_2025']})
        fm={'TTS GMV':'${:,.0f}'}
        if b['has_amz']:md['AMZ Sales']=b['amz_2025'];md['AMZ Organic']=b['org_2025'];md['Ad Sales']=[a-o for a,o in zip(b['amz_2025'],b['org_2025'])];fm.update({'AMZ Sales':'${:,.0f}','AMZ Organic':'${:,.0f}','Ad Sales':'${:,.0f}'})
        st.dataframe(md.style.format(fm),use_container_width=True)

st.markdown("---");sec("Export")
ec=['brand','jan_tts','active_months','impressions','visitors','videos','live_streams','creators','affiliate_gmv']
en=['Brand',f'TTS GMV ({ml})','Active Mo.','Impressions','Visitors','Videos','Lives','Creators','Affiliate GMV']
if amz:ec+=['jan_amz','r_best','confidence','rate','attributed','capped'];en+=['AMZ Sales','r','Confidence','Rate','Attributed','Capped']
exp=df[ec].copy();exp.columns=en;csv=exp.to_csv(index=False)
st.download_button("📥 Download Brand Summary (CSV)",csv,"tts_lift_summary.csv","text/csv")
st.caption(f"Pattern × NextWave · TTS → Amazon Lift Model v4 · {ml} · {len(df)} brands")
