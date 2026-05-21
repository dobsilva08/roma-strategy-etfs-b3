import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time
import pytz

st.set_page_config(
    page_title="Roma Strategy — ETFs B3",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #e0e0e0; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    [data-testid="metric-container"] { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
    h1, h2, h3 { font-family: 'Courier New', monospace !important; }
    .stButton > button { background-color: #238636; color: white; border: none; border-radius: 6px; font-weight: bold; width: 100%; }
    .stButton > button:hover { background-color: #2ea043; }
    .info-box { background-color: #1c2d40; border: 1px solid #1f6feb; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; color: #58a6ff; font-family: 'Courier New', monospace; font-size: 0.9rem; }
    .signal-buy { background-color: #0d2818; border: 1px solid #238636; border-radius: 8px; padding: 12px 16px; margin: 6px 0; font-family: 'Courier New', monospace; }
    .warning-box { background-color: #2d1b00; border: 1px solid #f0883e; border-radius: 8px; padding: 12px 16px; margin-top: 20px; color: #f0883e; font-size: 0.8rem; }
    .footer { text-align: center; color: #666; font-size: 0.75rem; margin-top: 40px; font-family: 'Courier New', monospace; }
</style>
""", unsafe_allow_html=True)

ETFS_B3 = {
    "BOVA11": {"name": "iShares Ibovespa", "sector": "Renda Variável"},
    "SMAL11": {"name": "iShares Small Cap", "sector": "Renda Variável"},
    "IVVB11": {"name": "iShares S&P 500 (BRL)", "sector": "Internacional"},
    "SPY11":  {"name": "SPDR S&P 500 (BRL)", "sector": "Internacional"},
    "HASH11": {"name": "Hashdex Nasdaq Crypto", "sector": "Cripto"},
    "GOLD11": {"name": "Trend ETF Ouro", "sector": "Commodities"},
    "DIVO11": {"name": "IT Now Dividendos", "sector": "Dividendos"},
    "ECOO11": {"name": "iShares Carbono Eficiente", "sector": "ESG"},
    "FIND11": {"name": "Financeiro Index", "sector": "Financeiro"},
    "MATB11": {"name": "Materiais Básicos", "sector": "Materiais"},
    "UTIL11": {"name": "Utilidades", "sector": "Utilidades"},
    "AGRI11": {"name": "Trend ETF Agro", "sector": "Agronegócio"},
    "NTNB11": {"name": "Trend ETF IPCA+", "sector": "Renda Fixa"},
    "FIXA11": {"name": "Trend ETF Prefixado", "sector": "Renda Fixa"},
    "XFIX11": {"name": "XP Fixed Income ETF", "sector": "Renda Fixa"},
}

def get_etf_data(ticker, period=2):
    try:
        df = yf.download(ticker + ".SA", period="10d", interval="1d", auto_adjust=True, progress=False)
        if df is None or len(df) < period + 1:
            return None
        df = df.dropna()
        closes = df["Close"].values
        highs  = df["High"].values
        lows   = df["Low"].values
        min_n  = float(min(lows[-period - 1:-1]))
        max_n  = float(max(highs[-period - 1:-1]))
        close  = float(closes[-1])
        prev   = float(closes[-2])
        return {
            "ticker": ticker, "close": close, "prev_close": prev,
            "min_n": min_n, "max_n": max_n,
            "signal": "BUY" if close <= min_n else "WATCH",
            "change_pct": ((close - prev) / prev) * 100,
            "date": str(df.index[-1].date()),
        }
    except Exception:
        return None

def send_telegram(token, chat_id, message):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return (True, "Mensagem enviada! ✅") if r.status_code == 200 else (False, f"Erro {r.status_code}")
    except Exception as e:
        return False, str(e)

def build_alert_message(etf_info, meta):
    ts = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    return (
        f"🏗️ <b>ROMA STRATEGY — SINAL DE COMPRA</b>\n\n"
        f"📊 <b>ETF:</b> {etf_info['name']} (<code>{meta['ticker']}</code>)\n"
        f"💰 <b>Fechamento:</b> R$ {meta['close']:.2f}\n"
        f"📉 <b>Mín. período:</b> R$ {meta['min_n']:.2f}\n"
        f"📈 <b>Variação:</b> {meta['change_pct']:+.2f}%\n"
        f"📅 <b>Data:</b> {meta['date']}\n"
        f"🕐 <b>Sinal em:</b> {ts}\n\n"
        f"⚠️ <i>Não constitui recomendação de investimento.</i>"
    )

for key, val in [("bot_token",""),("chat_id",""),("alert_logs",[]),("period",2),("last_scan",None),("scan_results",[])]:
    if key not in st.session_state:
        st.session_state[key] = val

with st.sidebar:
    st.markdown("## 🏗️ Roma Strategy")
    st.markdown("---")
    page = st.radio("Nav", ["📊 Dashboard","🔔 Alert Center","📋 ETF Manager","📈 Analytics"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### ⚙️ Parâmetros")
    st.session_state.period = st.slider("Período (N candles)", 1, 10, st.session_state.period)
    st.markdown("---")
    st.markdown("### 🔑 Telegram")
    st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password", placeholder="110201543:AAH...")
    st.session_state.chat_id   = st.text_input("Chat ID",   value=st.session_state.chat_id,   placeholder="-1001234567890")
    st.markdown("---")
    st.markdown("<div style='color:#666;font-size:0.75rem;font-family:Courier New'>Roma Strategy v1.0<br>Dados via Yahoo Finance</div>", unsafe_allow_html=True)

if page == "📊 Dashboard":
    st.markdown("# 📊 Dashboard")
    st.markdown(f"<div class='info-box'>Estratégia Roma — Close ≤ Mín. dos últimos <b>{st.session_state.period}</b> candle(s) → Sinal de COMPRA.</div>", unsafe_allow_html=True)
    col1, _ = st.columns([1,3])
    with col1:
        run = st.button("🔍 Escanear ETFs agora")
    if run:
        results, prog = [], st.progress(0, text="Buscando...")
        total = len(ETFS_B3)
        for i,(ticker,info) in enumerate(ETFS_B3.items()):
            d = get_etf_data(ticker, st.session_state.period)
            if d:
                d.update(info)
                results.append(d)
            prog.progress((i+1)/total, text=f"Analisando {ticker}...")
            time.sleep(0.2)
        prog.empty()
        st.session_state.scan_results = results
        st.session_state.last_scan = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
    if st.session_state.last_scan:
        st.caption(f"Último scan: {st.session_state.last_scan}")
    results = st.session_state.scan_results
    if results:
        buys  = [r for r in results if r["signal"]=="BUY"]
        watch = [r for r in results if r["signal"]=="WATCH"]
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("ETFs Monitorados", len(results))
        c2.metric("✅ Sinais BUY", len(buys), delta=f"+{len(buys)}" if buys else None)
        c3.metric("⚪ Aguardando", len(watch))
        c4.metric("Período", f"N = {st.session_state.period}")
        st.markdown("---")
        if buys:
            st.markdown("### ✅ Sinais de COMPRA")
            for r in buys:
                cc = "#3fb950" if r["change_pct"]>=0 else "#f85149"
                st.markdown(f"<div class='signal-buy'><b style='color:#3fb950;font-size:1.1rem;'>BUY</b> &nbsp;│&nbsp; <b>{r['name']}</b> <span style='color:#58a6ff'>({r['ticker']})</span> &nbsp;│&nbsp; R$ {r['close']:.2f} &nbsp;│&nbsp; Mín: R$ {r['min_n']:.2f} &nbsp;│&nbsp; <b style='color:{cc}'>{r['change_pct']:+.2f}%</b></div>", unsafe_allow_html=True)
        else:
            st.info("Nenhum sinal de BUY no momento.")
        st.markdown("---")
        st.markdown("### 📋 Lista completa de ETFs")
        cols = ["ticker","name","sector","close","min_n","max_n","change_pct","signal","date"]
        df_d = pd.DataFrame(results)[cols].rename(columns={"ticker":"Ticker","name":"Nome","sector":"Setor","close":"Fechamento (R$)","min_n":f"Mín. N={st.session_state.period}","max_n":f"Máx. N={st.session_state.period}","change_pct":"Variação (%)","signal":"Sinal","date":"Data"})
        st.dataframe(df_d, use_container_width=True, hide_index=True)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)

elif page == "🔔 Alert Center":
    st.markdown("# 🔔 Alert Center")
    t1, t2 = st.tabs(["⚙️ Telegram Config","📋 Alert Logs"])
    with t1:
        st.markdown("### Telegram Bot Configuration")
        st.markdown("<div class='info-box'>1) Crie um bot com @BotFather &nbsp; 2) Obtenha Chat ID &nbsp; 3) Configure abaixo</div>", unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password", placeholder="123456789:ABCDef...")
        with c2:
            st.session_state.chat_id = st.text_input("Chat ID / Channel ID", value=st.session_state.chat_id, placeholder="-1001234567890")
        st.markdown("---")
        st.markdown("### Test Connection")
        tmsg = st.text_input("Test message", value="🏗️ Olá do Roma Strategy ETF Monitor!")
        cs,cc2 = st.columns(2)
        with cs:
            if st.button("📨 Send Test Message"):
                if not st.session_state.bot_token or not st.session_state.chat_id:
                    st.error("Preencha Token e Chat ID.")
                else:
                    ok, msg = send_telegram(st.session_state.bot_token, st.session_state.chat_id, tmsg)
                    st.success(msg) if ok else st.error(msg)
        with cc2:
            st.info("Configure BOT_TOKEN e CHAT_ID nos Secrets do Streamlit Cloud.")
        st.markdown("---")
        st.markdown("### 📖 Como obter seu Chat ID")
        st.markdown("1. Inicie conversa com seu bot\n2. Envie uma mensagem\n3. Acesse: https://api.telegram.org/bot<TOKEN>/getUpdates\n4. Copie o campo id dentro de chat")
        st.markdown("---")
        st.markdown("### 🚀 Enviar Alertas Ativos")
        st.markdown("<div class='info-box'>Envia alertas para os ETFs com sinal <b>BUY</b> no último scan.</div>", unsafe_allow_html=True)
        bnow = [r for r in st.session_state.scan_results if r["signal"]=="BUY"]
        if not bnow:
            st.warning("Nenhum sinal BUY. Execute o scan no Dashboard primeiro.")
        else:
            st.success(f"{len(bnow)} sinal(is) BUY disponível(is).")
            if st.button(f"📡 Enviar {len(bnow)} alerta(s)"):
                if not st.session_state.bot_token or not st.session_state.chat_id:
                    st.error("Configure Token e Chat ID.")
                else:
                    sent=0; errs=0
                    for r in bnow:
                        info2 = ETFS_B3.get(r["ticker"],{"name":r["ticker"]})
                        ok, resp = send_telegram(st.session_state.bot_token, st.session_state.chat_id, build_alert_message(info2,r))
                        st.session_state.alert_logs.insert(0,{"time":datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S"),"ticker":r["ticker"],"signal":"BUY","status":"✅" if ok else f"❌ {resp}","close":r["close"]})
                        sent+=ok; errs+=not ok; time.sleep(0.3)
                    if sent: st.success(f"{sent} alerta(s) enviado(s)!")
                    if errs: st.error(f"{errs} erro(s).")
    with t2:
        st.markdown("### 📋 Histórico de Alertas")
        if not st.session_state.alert_logs:
            st.info("Nenhum alerta enviado nesta sessão.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.alert_logs), use_container_width=True, hide_index=True)
            if st.button("🗑️ Limpar logs"):
                st.session_state.alert_logs = []; st.rerun()

elif page == "📋 ETF Manager":
    st.markdown("# 📋 ETF Manager")
    st.markdown("<div class='info-box'>Lista completa dos ETFs monitorados pela plataforma.</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"Ticker":k,"Nome":v["name"],"Setor":v["sector"]} for k,v in ETFS_B3.items()]), use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("### ℹ️ Sobre a cobertura")
    st.markdown("""
A plataforma monitora os principais ETFs listados na **B3**, cobrindo:
- **Renda Variável** — BOVA11, SMAL11
- **Internacional** — IVVB11, SPY11
- **Cripto** — HASH11
- **Commodities** — GOLD11, AGRI11
- **Dividendos** — DIVO11
- **ESG** — ECOO11
- **Setoriais** — FIND11, MATB11, UTIL11
- **Renda Fixa** — NTNB11, FIXA11, XFIX11
    """)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)

elif page == "📈 Analytics":
    st.markdown("# 📈 Analytics")
    st.markdown("<div class='info-box'>Análise dos sinais gerados no último scan.</div>", unsafe_allow_html=True)
    results = st.session_state.scan_results
    if not results:
        st.warning("Execute o scan no Dashboard primeiro.")
    else:
        df = pd.DataFrame(results)
        st.markdown("### 🗂️ Sinais por Setor")
        st.dataframe(df.groupby(["sector","signal"]).size().unstack(fill_value=0).reset_index(), use_container_width=True, hide_index=True)
        st.markdown("---")
        st.markdown("### 📊 Variação (%)")
        st.bar_chart(df.set_index("ticker")["change_pct"], use_container_width=True, color="#238636")
        st.markdown("---")
        st.markdown("### 🏆 Top 5 — Mais próximos de sinal BUY")
        df["dist_min"] = ((df["close"]-df["min_n"])/df["min_n"]*100).round(2)
        top5 = df[df["signal"]=="WATCH"].nsmallest(5,"dist_min")[["ticker","name","close","min_n","dist_min"]]
        st.info("Todos em BUY!") if top5.empty else st.dataframe(top5.rename(columns={"ticker":"Ticker","name":"Nome","close":"Fechamento","min_n":"Mín.","dist_min":"Distância (%)"}), use_container_width=True, hide_index=True)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)

st.markdown("<div class='footer'>🏗️ Roma Strategy ETF Monitor &nbsp;|&nbsp; Dados via Yahoo Finance &nbsp;|&nbsp; Fins educacionais</div>", unsafe_allow_html=True)
