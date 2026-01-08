#!/usr/bin/env python3
"""
Script completo per sentiment analysis e invio automatico via email
Include: RSS feeds, ForexFactory events, OpenAI analysis, matplotlib plot
"""

import os
import sys
import json
import requests
import feedparser
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO

print(f"Env: {os.path.abspath('.env') if os.path.exists('.env') else 'No .env found'}")
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY', '')
if api_key:
    print(f"Loaded KEY starts: {api_key[:7]} | len: {len(api_key)}")
else:
    print("WARNING: OPENAI_API_KEY not found!")

try:
    import openai
    print(f"OpenAI pkg: {openai.__version__} | mode=v1")
except ImportError:
    print("ERROR: openai package not installed")
    sys.exit(1)

MODEL = os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'
print(f"Model used: {MODEL}")

def fetch_rss_news():
    """Recupera news dai feed RSS"""
    feeds = [
        ('CNBC', 'https://www.cnbc.com/id/100003114/device/rss/rss.html'),
        ('MarketWatch', 'https://feeds.marketwatch.com/marketwatch/topstories'),
    ]
    all_news = []
    for name, url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                all_news.append({
                    'source': name,
                    'title': entry.get('title', ''),
                    'summary': entry.get('summary', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', '')
                })
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    return all_news

def fetch_forexfactory_events():
    """Scraping eventi ForexFactory prossime 16h"""
    try:
        url = 'https://www.forexfactory.com/calendar'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        rows = soup.find_all('tr', class_='calendar__row')
        for row in rows[:10]:
            try:
                impact = row.find('td', class_='calendar__impact')
                if impact and 'icon--ff-impact-red' in str(impact):
                    event_data = {
                        'currency': row.find('td', class_='calendar__currency').text.strip() if row.find('td', class_='calendar__currency') else '',
                        'event': row.find('span', class_='calendar__event-title').text.strip() if row.find('span', class_='calendar__event-title') else '',
                        'impact': 'HIGH'
                    }
                    events.append(event_data)
            except:
                continue
        return events[:5]
    except Exception as e:
        print(f"Error fetching ForexFactory: {e}")
        return []

def analyze_sentiment_with_openai(news, events):
    """Analisi sentiment tramite OpenAI"""
    news_summary = "\n".join([f"- {n['title']}" for n in news[:40]])
    events_summary = "\n".join([f"- {e['currency']}: {e['event']} ({e['impact']})" for e in events])
    prompt = f"""Analizza il sentiment di mercato e fornisci una risposta in formato JSON con: stance (RISK-ON/RISK-OFF/NEUTRAL), score (da -100 a +100), confidence (0.0-1.0), conclusion (breve frase).

News ({len(news)}):
{news_summary}

Eventi ForexFactory prossime 16h ({len(events)}):
{events_summary if events else 'Nessun evento high-impact'}

Rispondi SOLO con JSON valido."""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': 'Sei un analista finanziario esperto. Rispondi sempre in formato JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]
        content = content.strip()
        result = json.loads(content)
        return {
            'stance': result.get('stance', 'NEUTRAL'),
            'score': result.get('score', 0),
            'confidence': result.get('confidence', 0.5),
            'conclusion': result.get('conclusion', 'Analisi non disponibile')
        }
    except Exception as e:
        print(f"Error in OpenAI analysis: {e}")
        return {
            'stance': 'NEUTRAL',
            'score': 0,
            'confidence': 0.0,
            'conclusion': f'Errore nell\'analisi: {str(e)[:100]}'
        }

def create_sentiment_chart(sentiment_data):
    """Crea grafico sentiment e ritorna bytes dell'immagine"""
    fig, ax = plt.subplots(figsize=(10, 6))
    score = sentiment_data['score']
    stance = sentiment_data['stance']
    conf = sentiment_data['confidence']
    colors = ['red' if score < -30 else 'orange' if score < 30 else 'green']
    ax.barh(['Sentiment Score'], [score], color=colors)
    ax.set_xlim(-100, 100)
    ax.set_xlabel('Score (-100 = Max Risk-Off, +100 = Max Risk-On)')
    ax.set_title(f'Market Sentiment Analysis\n{stance} | Score: {score} | Confidence: {conf:.2f}', fontsize=14, fontweight='bold')
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1)
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf.read()

def send_email_signal(sentiment_data, news_count, events_count, chart_bytes):
    """Invia email con risultati analisi"""
    sender_email = os.getenv('EMAIL_FROM')
    sender_password = os.getenv('EMAIL_PASSWORD')
    recipient_email = os.getenv('EMAIL_TO', 'studiolegaleartax@gmail.com')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    if not sender_email or not sender_password:
        print("ERROR: Email credentials not configured")
        return False
    msg = MIMEMultipart('related')
    msg['Subject'] = f"Segnale Sentiment {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    html_body = f"""
<html>
<body>
<h2>Analisi Sentiment Completata</h2>
<p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
<p><strong>Stance:</strong> {sentiment_data['stance']}</p>
<p><strong>Score:</strong> {sentiment_data['score']}</p>
<p><strong>Confidence:</strong> {sentiment_data['confidence']:.2f}</p>
<p><strong>Inputs:</strong> news={news_count} | events(next 16h)={events_count}</p>
<hr>
<p><strong>Conclusione:</strong></p>
<p>{sentiment_data['conclusion']}</p>
<hr>
<p><img src="cid:sentiment_chart"></p>
<p><em>Generated by Sentiment Signal Automation</em></p>
</body>
</html>
"""
    msg.attach(MIMEText(html_body, 'html'))
    img = MIMEImage(chart_bytes)
    img.add_header('Content-ID', '<sentiment_chart>')
    img.add_header('Content-Disposition', 'inline', filename='sentiment_chart.png')
    msg.attach(img)
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
    print(f"\nAvvio analisi sentiment - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[1/4] Fetching RSS news...")
    news = fetch_rss_news()
    print(f"   Recuperate {len(news)} news")
    print("\n[2/4] Fetching ForexFactory events...")
    events = fetch_forexfactory_events()
    print(f"   Recuperati {len(events)} eventi high-impact")
    print("\n[3/4] Analyzing sentiment with OpenAI...")
    print(f"Inputs: news={len(news)} | events(next 16h)={len(events)}")
    sentiment_data = analyze_sentiment_with_openai(news, events)
    print(f"stance={sentiment_data['stance']} | score={sentiment_data['score']} | conf={sentiment_data['confidence']:.2f}")
    print(sentiment_data['conclusion'])
    print("\n[4/4] Creating chart and sending email...")
    chart_bytes = create_sentiment_chart(sentiment_data)
    success = send_email_signal(sentiment_data, len(news), len(events), chart_bytes)
    if success:
        print("\nProcesso completato con successo")
    else:
        print("\nWARNING: Email not sent (credentials not configured)")
        print("Analisi completata comunque con successo")
    return 0

if __name__ == '__main__':
    sys.exit(main())
