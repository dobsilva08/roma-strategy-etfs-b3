# 🏗️ Roma Strategy — Monitor de ETFs B3

Plataforma Streamlit que implementa a estratégia Roma no gráfico diário, monitorando os principais ETFs da B3 e enviando alertas de compra via Telegram.

## ⚙️ Lógica da Estratégia

```
Periodo := N (padrão = 2)
Min_N := Lowest(Low, Periodo)   → mínima dos últimos N candles anteriores
Max_N := Highest(High, Periodo) → máxima dos últimos N candles anteriores

SINAL DE COMPRA: Close atual ≤ Min_N do candle anterior
```

## 🚀 Deploy no Streamlit Cloud

1. Fork ou acesse este repositório no GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Selecione o repositório, branch `main`, arquivo `app.py`
4. Python version: **3.11**
5. Clique em **Deploy**

### Variáveis de Ambiente (Secrets)

No painel do Streamlit Cloud, vá em **Settings → Secrets** e adicione:

```toml
BOT_TOKEN = "seu_token_aqui"
CHAT_ID   = "seu_chat_id_aqui"
```

## 📡 Configurar Bot do Telegram

1. Abra o Telegram → busque **@BotFather** → envie `/newbot`
2. Copie o token gerado
3. Para obter o Chat ID: envie uma mensagem ao bot e acesse:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Insira token e Chat ID na barra lateral da plataforma

## 📦 Estrutura

```
roma-strategy-etfs-b3/
├── app.py           # Aplicação principal
├── requirements.txt # Dependências Python
└── README.md        # Este arquivo
```

## 🔔 Funcionamento dos Alertas

| Condição | Ação |
|---|---|
| Close ≤ Mín. do período anterior | ✅ Sinal de COMPRA + alerta Telegram |
| Sem sinal | ⚪ Status "Aguardando" |

A mensagem no Telegram inclui: nome do ETF, ticker, preço de fechamento, mínima do período e horário do sinal.

## 📊 ETFs Monitorados

| Ticker | Nome | Setor |
|---|---|---|
| BOVA11 | iShares Ibovespa | Renda Variável |
| SMAL11 | iShares Small Cap | Renda Variável |
| IVVB11 | iShares S&P 500 (BRL) | Internacional |
| SPY11 | SPDR S&P 500 (BRL) | Internacional |
| HASH11 | Hashdex Nasdaq Crypto | Cripto |
| GOLD11 | Trend ETF Ouro | Commodities |
| DIVO11 | IT Now Dividendos | Dividendos |
| ECOO11 | iShares Carbono Eficiente | ESG |
| FIND11 | Financeiro Index | Financeiro |
| MATB11 | Materiais Básicos | Materiais |
| UTIL11 | Utilidades | Utilidades |
| AGRI11 | Trend ETF Agro | Agronegócio |
| NTNB11 | Trend ETF IPCA+ | Renda Fixa |
| FIXA11 | Trend ETF Prefixado | Renda Fixa |
| XFIX11 | XP Fixed Income ETF | Renda Fixa |

## ⚠️ Aviso

Esta plataforma é para fins **educacionais e de monitoramento**.
Não constitui recomendação de investimento.
