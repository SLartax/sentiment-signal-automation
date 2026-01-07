#!/usr/bin/env python3
"""
Script per sentiment analysis e invio automatico via email
Versione semplificata per GitHub Actions
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import requests
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

def fetch_rss_news():
    """Recupera news dai feed RSS"""
    feeds = [
        ('CNBC', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
        ('MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories'),
    ]
    
    news_items = []
    for source, url in feeds:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                # Parsing XML semplificato
                news_items.append({'source': source, 'status': 'OK'})
        except Exception as e:
            print(f"Errore nel recupero di {source}: {e}")
    
    return news_items

def analyze_sentiment():
    """Esegue l'analisi di sentiment tramite OpenAI"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY non trovata")
    
    # Recupera news
    news = fetch_rss_news()
    
    # Prepara la chiamata a OpenAI
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': os.getenv('OPENAI_MODEL') or 'gpt-4o-mini',        'messages': [
            {
                'role': 'system',
                'content': 'Analizza il sentiment di mercato e fornisci una risposta in formato JSON con: stance (RISK-ON/RISK-OFF/NEUTRAL), score (-100 a 100), conclusion (breve)'
            },
            {
                'role': 'user',
                'content': f'Analizza il sentiment attuale dei mercati basandoti su queste fonti: {json.dumps(news)}'
            }
        ],
        'temperature': 0.0
    }
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Rimuovi markdown code blocks se presenti
            content = content.strip()
            if content.startswith('```'):
                # Rimuovi ```json o ``` all'inizio
                content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                # Rimuovi ``` alla fine
                content = content.rsplit('```', 1)[0]
            content = content.strip()
            
            # Prova a estrarre JSON dalla risposta
            try:
                sentiment_data = json.loads(content)
            except:
                # Se non è JSON, crea una struttura base
                sentiment_data = {
                    'stance': 'NEUTRAL',
                    'score': 0,
                'conclusion': content[:200]                }
            
            return sentiment_data
        else:
            print(f"Errore API OpenAI: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Errore nell'analisi: {e}")
        return None

def send_email_signal(sentiment_data):
    """Invia il segnale via email"""
    
    # Recupera credenziali email da variabili d'ambiente
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL', 'studiolegaleartax@gmail.com')
    
    if not all([sender_email, sender_password]):
        raise ValueError("Credenziali email non configurate")
    
    # Prepara il messaggio
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Segnale Sentiment Market - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # Costruisci il corpo dell'email
    stance = sentiment_data.get('stance', 'NEUTRAL')
    score = sentiment_data.get('score', 0)
    conclusion = sentiment_data.get('conclusion', 'Nessuna conclusione disponibile')
    
    text_body = f"""
SEGNALE DI SENTIMENT ANALYSIS
==============================

Timestamp: {datetime.now().strftime('%d/%m/%Y ore %H:%M CET')}

STANCE: {stance}
SCORE: {score}/100

CONCLUSIONE:
{conclusion}

---
Questo è un segnale automatico generato dal sistema di sentiment analysis.
Non costituisce consulenza finanziaria.
    """
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2 style="color: #1f2a44;">Segnale di Sentiment Analysis</h2>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%d/%m/%Y ore %H:%M CET')}</p>
        
        <div style="background-color: {'#2a9d8f' if stance == 'RISK-ON' else '#e63946' if stance == 'RISK-OFF' else '#6c757d'}; 
                    color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
          <h3 style="margin: 0;">STANCE: {stance}</h3>
          <p style="font-size: 24px; margin: 10px 0;"><strong>Score: {score}/100</strong></p>
        </div>
        
        <h4>Conclusione:</h4>
        <p style="background-color: #f7f7fb; padding: 15px; border-left: 4px solid #1f2a44;">
          {conclusion}
        </p>
        
        <hr style="margin-top: 30px;">
        <p style="font-size: 12px; color: #6c757d;">
          Questo è un segnale automatico generato dal sistema di sentiment analysis.<br>
          Non costituisce consulenza finanziaria.
        </p>
      </body>
    </html>
    """
    
    # Aggiungi entrambe le versioni
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(html_body, 'html')
    msg.attach(part1)
    msg.attach(part2)
    
    # Invia l'email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f"Email inviata con successo a {recipient_email}")
        return True
        
    except Exception as e:
        print(f"Errore nell'invio dell'email: {e}")
        return False

def main():
    """Funzione principale"""
    print(f"Avvio analisi sentiment - {datetime.now()}")
    
    try:
        # Esegui l'analisi
        sentiment_data = analyze_sentiment()
        
        if sentiment_data:
            print(f"Analisi completata: {sentiment_data.get('stance')} (Score: {sentiment_data.get('score')})")
            
            # Invia l'email
            success = send_email_signal(sentiment_data)
            
            if success:
                print("Processo completato con successo")
                return 0
            else:
                print("Errore nell'invio dell'email")
                return 1
        else:
            print("Errore nell'analisi del sentiment")
            return 1
            
    except Exception as e:
        print(f"Errore fatale: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
