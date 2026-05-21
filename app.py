import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time
import pytz
import json

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
    .signal-buy { background-color: #0d2818; border: 1px solid #238636; border-radius: 8px; padding: 14px 18px; margin: 8px 0; font-family: 'Courier New', monospace; }
    .signal-exit { background-color: #1a1a2e; border: 1px solid #f0883e; border-radius: 8px; padding: 10px 16px; margin: 4px 0; font-family: 'Courier New', monospace; font-size: 0.85rem; }
    .warning-box { background-color: #2d1b00; border: 1px solid #f0883e; border-radius: 8px; padding: 12px 16px; margin-top: 20px; color: #f0883e; font-size: 0.8rem; }
    .footer { text-align: center; color: #666; font-size: 0.75rem; margin-top: 40px; font-family: 'Courier New', monospace; }
    .tag-buy { background-color: #238636; color: white; border-radius: 4px; padding: 2px 8px; font-size: 0.8rem; font-weight: bold; }
    .tag-watch { background-color: #444; color: #ccc; border-radius: 4px; padding: 2px 8px; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ── ETFs padrão ──────────────────────────────────────────────────────────────
DEFAULT_ETFS = {
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

# ── Funções auxiliares ──────────────────────────────────────────────────────

def get_etf_data(ticker, period=2):
    """Baixa dados e aplica Estratégia Roma com cálculo de saída."""
    try:
        df = yf.download(ticker + ".SA", period="15d", interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or len(df) < period + 2:
            return None
        df = df.dropna()
        closes = df["Close"].values
        highs  = df["High"].values
        lows   = df["Low"].values

        # Janela: penultimo conjunto de N candles (excluindo o atual)
        min_n  = float(min(lows[-period - 1:-1]))
        max_n  = float(max(highs[-period - 1:-1]))
        close  = float(closes[-1])
        prev   = float(closes[-2])

        # Média das 2 maiores máximas do período (alvo de saída)
        last_highs = sorted([float(h) for h in highs[-period - 1:-1]], reverse=True)
        avg_top2   = sum(last_highs[:2]) / 2 if len(last_highs) >= 2 else max_n

        # Stop: 1% abaixo do preço de entrada (close atual se sinal BUY)
        stop_loss  = round(close * 0.99, 2)

        signal = "BUY" if close <= min_n else "WATCH"

        return {
            "ticker":    ticker,
            "close":     close,
            "prev":      prev,
            "min_n":     min_n,
            "max_n":     max_n,
            "avg_top2":  round(avg_top2, 2),
            "stop":      stop_loss,
            "signal":    signal,
            "change_pct": ((close - prev) / prev) * 100,
            "date":      str(df.index[-1].date()),
            "upside_pct": round(((avg_top2 - close) / close) * 100, 2) if signal == "BUY" else None,
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


def build_alert_message(name, meta):
    ts = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    return (
        f"🏗️ <b>ROMA STRATEGY — SINAL DE COMPRA</b>\n\n"
        f"📊 <b>ETF:</b> {name} (<code>{meta['ticker']}</code>)\n"
        f"💰 <b>Entrada:</b> R$ {meta['close']:.2f}\n"
        f"🎯 <b>Alvo (méd. 2 máx):</b> R$ {meta['avg_top2']:.2f} (+{meta['upside_pct']:.2f}%)\n"
        f"🛡️ <b>Stop (1%):</b> R$ {meta['stop']:.2f}\n"
        f"📉 <b>Mín. período:</b> R$ {meta['min_n']:.2f}\n"
        f"📈 <b>Variação:</b> {meta['change_pct']:+.2f}%\n"
        f"📅 <b>Data:</b> {meta['date']}\n"
        f"🕐 <b>Sinal em:</b> {ts}\n\n"
        f"⚠️ <i>Não constitui recomendação de investimento.</i>"
    )


def run_scan(assets, period):
    """Executa o scan em todos os ativos."""
    results = []
    prog = st.progress(0, text="Buscando dados...")
    total = len(assets)
    for i, (ticker, info) in enumerate(assets.items()):
        d = get_etf_data(ticker, period)
        if d:
            d["name"]   = info.get("name", ticker)
            d["sector"] = info.get("sector", "Personalizado")
            d["custom"] = info.get("custom", False)
            results.append(d)
        prog.progress((i + 1) / total, text=f"Analisando {ticker}...")
        time.sleep(0.15)
    prog.empty()
    return results

# ── Session State ───────────────────────────────────────────────────────────
defaults = {
    "bot_token": "", "chat_id": "", "alert_logs": [],
    "period": 2, "last_scan": None, "scan_results": [],
    "custom_assets": {},   # ticker -> {name, sector, custom: True}
    "auto_scanned": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Ativos combinados: padrão + personalizados
def all_assets():
    merged = dict(DEFAULT_ETFS)
    merged.update(st.session_state.custom_assets)
    return merged

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏗️ Roma Strategy")
    st.markdown("---")
    page = st.radio("Nav", [
        "📊 Dashboard",
        "🔔 Alert Center",
        "➕ Gerenciar Ativos",
        "📋 ETF Manager",
        "📈 Analytics",
    ], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### ⚙️ Parâmetros")
    st.session_state.period = st.slider("Período (N candles)", 1, 10, st.session_state.period)
    st.markdown("---")
    st.markdown("### 🔑 Telegram")
    st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password", placeholder="110201543:AAH...")
    st.session_state.chat_id   = st.text_input("Chat ID",   value=st.session_state.chat_id,   placeholder="-1001234567890")
    st.markdown("---")
    total_assets = len(all_assets())
    st.markdown(f"<div style='color:#666;font-size:0.75rem;font-family:Courier New'>Roma Strategy v2.0<br>Ativos monitorados: {total_assets}<br>Dados via Yahoo Finance</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.markdown("# 📊 Dashboard")
    st.markdown(
        f"<div class='info-box'>"
        f"🏗️ Estratégia Roma — <b>Sinal de COMPRA</b> quando Close ≤ Mín. dos últimos <b>{st.session_state.period}</b> candle(s).<br>"
        f"🎯 <b>Saída:</b> Preço toca a média das 2 maiores máximas do período &nbsp;│&nbsp; "
        f"🛡️ <b>Stop:</b> 1% abaixo da entrada"
        f"</div>",
        unsafe_allow_html=True,
    )

    col_scan, col_auto, _ = st.columns([1, 1, 2])
    with col_scan:
        manual_scan = st.button("🔍 Escanear agora")
    with col_auto:
        auto_on = st.toggle("Auto-scan ao abrir", value=True)

    # Auto-scan na primeira carga
    if auto_on and not st.session_state.auto_scanned:
        st.session_state.scan_results = run_scan(all_assets(), st.session_state.period)
        st.session_state.last_scan = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")
        st.session_state.auto_scanned = True

    if manual_scan:
        st.session_state.scan_results = run_scan(all_assets(), st.session_state.period)
        st.session_state.last_scan = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")

    if st.session_state.last_scan:
        st.caption(f"Último scan: {st.session_state.last_scan}")

    results = st.session_state.scan_results
    if results:
        buys  = [r for r in results if r["signal"] == "BUY"]
        watch = [r for r in results if r["signal"] == "WATCH"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Ativos Monitorados", len(results))
        c2.metric("✅ Sinais BUY", len(buys), delta=f"+{len(buys)}" if buys else None)
        c3.metric("⚪ Aguardando", len(watch))
        c4.metric("Período N", f"{st.session_state.period} candles")

        st.markdown("---")

        # ── Sinais de COMPRA com saída e stop ─────────────────────────────────
        if buys:
            st.markdown(f"### ✅ {len(buys)} Sinal(is) de COMPRA Ativo(s)")
            for r in buys:
                cc = "#3fb950" if r["change_pct"] >= 0 else "#f85149"
                upside_str = f"+{r['upside_pct']:.2f}%" if r["upside_pct"] else ""
                badge = "<span style='background:#ff6b35;color:#fff;border-radius:4px;padding:1px 6px;font-size:0.75rem;margin-left:6px'>CUSTOM</span>" if r.get("custom") else ""
                st.markdown(
                    f"<div class='signal-buy'>"
                    f"<span class='tag-buy'>BUY</span>{badge} &nbsp;"
                    f"<b style='font-size:1.05rem'>{r['name']}</b> "
                    f"<span style='color:#58a6ff'>({r['ticker']})</span>"
                    f" &nbsp;│&nbsp; Setor: <i>{r['sector']}</i><br>"
                    f"💰 <b>Entrada:</b> R$ {r['close']:.2f} &nbsp;"
                    f"<span style='color:{cc}'>({r['change_pct']:+.2f}%)</span>"
                    f" &nbsp;│&nbsp; "
                    f"🎯 <b>Alvo:</b> <span style='color:#3fb950'>R$ {r['avg_top2']:.2f}</span>"
                    f" <span style='color:#888;font-size:0.85rem'>({upside_str})</span>"
                    f" &nbsp;│&nbsp; "
                    f"🛡️ <b>Stop:</b> <span style='color:#f85149'>R$ {r['stop']:.2f}</span>"
                    f"<div class='signal-exit'>"
                    f"📌 Saída: quando preço ≥ média 2 máx (R$ {r['avg_top2']:.2f}) &nbsp;| "
                    f"Stop: R$ {r['stop']:.2f} (1% abaixo da entrada) &nbsp;| "
                    f"Mín. período: R$ {r['min_n']:.2f}"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("⚪ Nenhum sinal de BUY no momento. Aguardando condição: Close ≤ Mínima do período anterior.")

        st.markdown("---")

        # Tabela completa
        st.markdown("### 📋 Lista completa de ativos")
        rows = []
        for r in results:
            rows.append({
                "Ticker": r["ticker"],
                "Nome": r["name"],
                "Setor": r["sector"],
                "Fechamento": f"R$ {r['close']:.2f}",
                f"Mín N={st.session_state.period}": f"R$ {r['min_n']:.2f}",
                "Alvo Saída": f"R$ {r['avg_top2']:.2f}",
                "Stop (1%)": f"R$ {r['stop']:.2f}",
                "Variação": f"{r['change_pct']:+.2f}%",
                "Sinal": r["signal"],
                "Data": r["date"],
            })
        df_display = pd.DataFrame(rows)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ALERT CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔔 Alert Center":
    st.markdown("# 🔔 Alert Center")
    t1, t2 = st.tabs(["⚙️ Telegram Config", "📋 Alert Logs"])

    with t1:
        st.markdown("### Telegram Bot Configuration")
        st.markdown("<div class='info-box'>1) Crie um bot com @BotFather &nbsp; 2) Obtenha Chat ID &nbsp; 3) Configure abaixo</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.bot_token = st.text_input("Bot Token", value=st.session_state.bot_token, type="password", placeholder="123456789:ABCDef...")
        with c2:
            st.session_state.chat_id = st.text_input("Chat ID", value=st.session_state.chat_id, placeholder="-1001234567890")
        st.markdown("---")
        st.markdown("### Test Connection")
        tmsg = st.text_input("Test message", value="🏗️ Olá do Roma Strategy ETF Monitor!")
        cs, cc2 = st.columns(2)
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
        st.markdown("### 🚀 Enviar Alertas BUY Ativos")
        st.markdown("<div class='info-box'>Envia alertas completos (entrada, alvo e stop) para os ETFs com sinal <b>BUY</b>.</div>", unsafe_allow_html=True)
        bnow = [r for r in st.session_state.scan_results if r["signal"] == "BUY"]
        if not bnow:
            st.warning("Nenhum sinal BUY. Execute o scan no Dashboard primeiro.")
        else:
            st.success(f"{len(bnow)} sinal(is) BUY disponível(is) para envio.")
            if st.button(f"📡 Enviar {len(bnow)} alerta(s)"):
                if not st.session_state.bot_token or not st.session_state.chat_id:
                    st.error("Configure Token e Chat ID.")
                else:
                    sent = errs = 0
                    assets = all_assets()
                    for r in bnow:
                        name = assets.get(r["ticker"], {}).get("name", r["ticker"])
                        ok, resp = send_telegram(
                            st.session_state.bot_token,
                            st.session_state.chat_id,
                            build_alert_message(name, r),
                        )
                        st.session_state.alert_logs.insert(0, {
                            "Hora": datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S"),
                            "Ticker": r["ticker"], "Sinal": "BUY",
                            "Entrada": f"R$ {r['close']:.2f}",
                            "Alvo": f"R$ {r['avg_top2']:.2f}",
                            "Stop": f"R$ {r['stop']:.2f}",
                            "Status": "✅ Enviado" if ok else f"❌ {resp}",
                        })
                        sent += ok; errs += not ok; time.sleep(0.3)
                    if sent: st.success(f"{sent} alerta(s) enviado(s) com sucesso!")
                    if errs: st.error(f"{errs} erro(s) ao enviar.")

    with t2:
        st.markdown("### 📋 Histórico de Alertas")
        if not st.session_state.alert_logs:
            st.info("Nenhum alerta enviado nesta sessão.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.alert_logs), use_container_width=True, hide_index=True)
            if st.button("🗑️ Limpar logs"):
                st.session_state.alert_logs = []
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# GERENCIAR ATIVOS (NOVO)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "➕ Gerenciar Ativos":
    st.markdown("# ➕ Gerenciar Ativos")
    st.markdown(
        "<div class='info-box'>"
        "Adicione qualquer ativo da B3 ou bolsas internacionais para monitorar além dos ETFs padrão. "
        "Para ativos da B3 basta digitar o ticker (ex: PETR4, VALE3). "
        "Para ativos internacionais use o ticker do Yahoo Finance (ex: AAPL, MSFT)."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Adicionar novo ativo ─────────────────────────────────────────────────
    st.markdown("### ➕ Adicionar novo ativo")
    with st.form("add_asset_form"):
        ca, cb, cc_col = st.columns([1, 2, 1])
        with ca:
            new_ticker = st.text_input("Ticker", placeholder="Ex: PETR4, VALE3, AAPL").upper().strip()
        with cb:
            new_name = st.text_input("Nome / Descrição", placeholder="Ex: Petrobras PN")
        with cc_col:
            new_sector = st.text_input("Setor", placeholder="Ex: Energia, Tech")
        submitted = st.form_submit_button("➕ Adicionar ativo", use_container_width=True)

    if submitted:
        if not new_ticker:
            st.error("Informe o ticker do ativo.")
        elif new_ticker in DEFAULT_ETFS:
            st.warning(f"{new_ticker} já faz parte dos ETFs padrão.")
        elif new_ticker in st.session_state.custom_assets:
            st.warning(f"{new_ticker} já está na lista personalizada.")
        else:
            # Valida se o ticker existe no Yahoo Finance
            with st.spinner(f"Validando {new_ticker}..."):
                suffix = ".SA" if len(new_ticker) <= 6 and new_ticker.isalpha() or (len(new_ticker) == 5 and new_ticker[-1].isdigit()) else ".SA"
                test_sym = new_ticker + suffix
                test_df = yf.download(test_sym, period="5d", progress=False)
                if test_df is None or len(test_df) == 0:
                    # Tenta sem .SA (ativo internacional)
                    test_df = yf.download(new_ticker, period="5d", progress=False)
                    if test_df is None or len(test_df) == 0:
                        st.error(f"Ticker '{new_ticker}' não encontrado no Yahoo Finance. Verifique e tente novamente.")
                    else:
                        st.session_state.custom_assets[new_ticker] = {
                            "name": new_name or new_ticker,
                            "sector": new_sector or "Internacional",
                            "custom": True,
                        }
                        st.success(f"✅ {new_ticker} adicionado com sucesso!")
                        st.session_state.auto_scanned = False
                        st.rerun()
                else:
                    st.session_state.custom_assets[new_ticker] = {
                        "name": new_name or new_ticker,
                        "sector": new_sector or "Personalizado",
                        "custom": True,
                    }
                    st.success(f"✅ {new_ticker} adicionado com sucesso!")
                    st.session_state.auto_scanned = False
                    st.rerun()

    st.markdown("---")

    # ── Ativos personalizados ────────────────────────────────────────────────
    st.markdown(f"### 📝 Ativos personalizados ({len(st.session_state.custom_assets)})")
    if not st.session_state.custom_assets:
        st.info("Nenhum ativo personalizado ainda. Adicione acima!")
    else:
        for ticker, info in list(st.session_state.custom_assets.items()):
            col_t, col_n, col_s, col_del = st.columns([1, 2, 1, 1])
            col_t.markdown(f"**{ticker}**")
            col_n.markdown(info["name"])
            col_s.markdown(f"_{info['sector']}_")
            with col_del:
                if st.button(f"🗑️ Remover", key=f"del_{ticker}"):
                    del st.session_state.custom_assets[ticker]
                    st.session_state.auto_scanned = False
                    st.rerun()

    st.markdown("---")

    # ── ETFs padrão (read-only) ────────────────────────────────────────────
    st.markdown(f"### 📦 ETFs padrão ({len(DEFAULT_ETFS)}) — sempre monitorados")
    df_default = pd.DataFrame([
        {"Ticker": k, "Nome": v["name"], "Setor": v["sector"]}
        for k, v in DEFAULT_ETFS.items()
    ])
    st.dataframe(df_default, use_container_width=True, hide_index=True)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ETF MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 ETF Manager":
    st.markdown("# 📋 ETF Manager")
    st.markdown("<div class='info-box'>Visão geral de todos os ativos monitorados.</div>", unsafe_allow_html=True)
    combined = all_assets()
    df_all = pd.DataFrame([
        {"Ticker": k, "Nome": v["name"], "Setor": v["sector"],
         "Tipo": "Personalizado 🔶" if v.get("custom") else "ETF Padrão"}
        for k, v in combined.items()
    ])
    st.metric("Total de ativos", len(df_all))
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 Analytics":
    st.markdown("# 📈 Analytics")
    st.markdown("<div class='info-box'>Análise dos sinais gerados no último scan.</div>", unsafe_allow_html=True)
    results = st.session_state.scan_results
    if not results:
        st.warning("Execute o scan no Dashboard primeiro.")
    else:
        df = pd.DataFrame(results)
        buys = [r for r in results if r["signal"] == "BUY"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ativos", len(results))
        c2.metric("✅ BUY", len(buys))
        c3.metric("Melhor Upside", f"{max((r['upside_pct'] or 0) for r in buys):.2f}%" if buys else "—")

        st.markdown("---")
        st.markdown("### 🗂️ Sinais por Setor")
        st.dataframe(
            df.groupby(["sector", "signal"]).size().unstack(fill_value=0).reset_index(),
            use_container_width=True, hide_index=True,
        )
        st.markdown("---")
        st.markdown("### 📊 Variação (%)")
        st.bar_chart(df.set_index("ticker")["change_pct"], use_container_width=True, color="#238636")

        if buys:
            st.markdown("---")
            st.markdown("### 🎯 Oportunidades BUY — Risco x Retorno")
            rr_rows = []
            for r in buys:
                risk  = round((r["close"] - r["stop"]) / r["close"] * 100, 2)
                gain  = r["upside_pct"] or 0
                rr    = round(gain / risk, 2) if risk > 0 else 0
                rr_rows.append({"Ticker": r["ticker"], "Nome": r["name"],
                                 "Entrada": f"R$ {r['close']:.2f}",
                                 "Alvo": f"R$ {r['avg_top2']:.2f}",
                                 "Stop": f"R$ {r['stop']:.2f}",
                                 "Ganho %": f"+{gain:.2f}%",
                                 "Risco %": f"-{risk:.2f}%",
                                 "R/R": f"{rr:.1f}x"})
            st.dataframe(pd.DataFrame(rr_rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🏆 Top 5 — Mais próximos de sinal BUY")
        df["dist_min"] = ((df["close"] - df["min_n"]) / df["min_n"] * 100).round(2)
        top5 = df[df["signal"] == "WATCH"].nsmallest(5, "dist_min")[["ticker","name","close","min_n","dist_min"]]
        if top5.empty:
            st.info("Todos em BUY!")
        else:
            st.dataframe(top5.rename(columns={
                "ticker":"Ticker","name":"Nome",
                "close":"Fechamento","min_n":"Mín.","dist_min":"Distância (%)",
            }), use_container_width=True, hide_index=True)
    st.markdown("<div class='warning-box'>⚠️ Fins educacionais. Não constitui recomendação de investimento.</div>", unsafe_allow_html=True)


# ── Rodapé ──────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='footer'>"
    "🏗️ Roma Strategy ETF Monitor v2.0 &nbsp;|&nbsp; "
    "Dados via Yahoo Finance &nbsp;|&nbsp; Fins educacionais"
    "</div>",
    unsafe_allow_html=True,
)
