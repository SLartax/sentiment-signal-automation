# 📊 Sentiment Signal Automation

Sistema automatico per l'invio di segnali di sentiment analysis via email alle 17:30 CET

## 🎯 Descrizione

Questo sistema esegue automaticamente un'analisi del sentiment dei mercati finanziari utilizzando OpenAI GPT e invia un segnale via email ogni giorno alle 17:30 CET tramite GitHub Actions.

### Caratteristiche principali:
- ✅ **Esecuzione automatica** schedulata alle 17:30 CET (ogni giorno feriale)
- 📧 **Invio email automatico** con risultati dell'analisi
- 🤖 **Analisi AI** tramite modelli OpenAI (GPT-4o-mini o superiori)
- 📰 **Feed RSS** da CNBC, MarketWatch e altre fonti finanziarie
- 🎨 **Email HTML formattata** con colori basati su RISK-ON/RISK-OFF/NEUTRAL

## 📋 Prerequisiti

1. **Account GitHub** (per eseguire il workflow)
2. **API Key OpenAI** ([ottieni qui](https://platform.openai.com/api-keys))
3. **Account email** con accesso SMTP (Gmail consigliato)
   - Per Gmail: genera una [App Password](https://myaccount.google.com/apppasswords)

## ⚙️ Configurazione

### Passo 1: Configura i Secret di GitHub

Vai su: `https://github.com/SLartax/sentiment-signal-automation/settings/secrets/actions`

Aggiungi i seguenti secret:

| Nome Secret | Descrizione | Esempio |
|------------|-------------|---------|
| `OPENAI_API_KEY` | La tua API key di OpenAI | `sk-...` |
| `OPENAI_MODEL` | Modello da usare (opzionale) | `gpt-4o-mini` |
| `SENDER_EMAIL` | Email mittente | `tuaemail@gmail.com` |
| `SENDER_PASSWORD` | Password app Gmail | `abcd efgh ijkl mnop` |
| `RECIPIENT_EMAIL` | Email destinatario | `studiolegaleartax@gmail.com` |
| `SMTP_SERVER` | Server SMTP (opzionale) | `smtp.gmail.com` |
| `SMTP_PORT` | Porta SMTP (opzionale) | `587` |

### Passo 2: Attiva GitHub Actions

1. Vai su tab "Actions" del repository
2. Se richiesto, abilita i workflow
3. Il workflow `Daily Sentiment Signal` si attiverà automaticamente alle 17:30 CET

### Passo 3: Testa manualmente (opzionale)

Puoi testare il sistema manualmente:
1. Vai su "Actions"
2. Seleziona "Daily Sentiment Signal"
3. Clicca "Run workflow"
4. Scegli "Run workflow" per eseguire immediatamente

## 📂 Struttura del Progetto

```
sentiment-signal-automation/
├── .github/
│   └── workflows/
│       └── daily_signal.yml      # GitHub Actions workflow
├── send_signal_email.py          # Script principale
├── requirements.txt              # Dipendenze Python
├── .env.example                  # Template per variabili d'ambiente
└── README.md                     # Questa documentazione
```

## 🔧 Come Funziona

1. **Schedulazione**: GitHub Actions esegue il workflow ogni giorno alle 17:30 CET
2. **Raccolta Dati**: Lo script raccoglie news dai feed RSS configurati
3. **Analisi**: OpenAI GPT analizza il sentiment e genera una valutazione
4. **Formato**: Il risultato viene formattato in HTML con colori RISK-ON/OFF
5. **Invio**: L'email viene inviata automaticamente all'indirizzo configurato

## 📧 Formato Email

L'email contiene:
- **Timestamp** dell'analisi
- **STANCE**: RISK-ON, RISK-OFF o NEUTRAL
- **Score**: valore da -100 a +100
- **Conclusione**: sintesi del sentiment con motivazioni

## 🛠️ Sviluppo Locale

Per testare lo script in locale:

```bash
# Installa dipendenze
pip install -r requirements.txt

# Crea un file .env con i tuoi secret (vedi .env.example)
cp .env.example .env
# Modifica .env con i tuoi valori reali

# Esegui lo script
python send_signal_email.py
```

## 🚨 Troubleshooting

### Il workflow non si avvia
- Verifica che GitHub Actions sia abilitato nel repository
- Controlla i log in "Actions" per eventuali errori

### Email non ricevuta
- Verifica che i secret email siano configurati correttamente
- Per Gmail, assicurati di usare una "App Password" e non la password normale
- Controlla la cartella spam

### Errore OpenAI
- Verifica che la tua API key sia valida e abbia credito
- Controlla i limiti di rate della tua API key

## 📝 Note

- Il sistema usa il fuso orario UTC per la schedulazione. La conversione a CET è gestita nel cron (16:30 UTC = 17:30 CET in inverno)
- Durante l'ora legale (estate), potrebbe essere necessario modificare il cron a 15:30 UTC
- Il recipient email di default è `studiolegaleartax@gmail.com`
- Questo sistema NON costituisce consulenza finanziaria

## 🔒 Sicurezza

- ⚠️ **Mai committare** secret o password nel repository
- ✅ Usa **sempre** i GitHub Secrets per dati sensibili  
- ✅ Per Gmail, usa **App Passwords** invece della password principale

## 📄 Licenza

Questo progetto è di uso interno. Tutti i diritti riservati.

---

**Ultimo aggiornamento**: Gennaio 2026  
**Maintainer**: SLartax
