#!/usr/bin/env python3
"""
LegalBandi Monitor - Sistema automatico per monitoraggio bandi pubblici avvocati
Controlla settimanalmente i bandi pubblici per avvocati collaboratori (libero foro)
e invia report via email
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
import pytz
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import re

load_dotenv()

# Configurazione OpenAI
try:
    import openai
    api_key = os.getenv('OPENAI_API_KEY', '')
    MODEL = os.getenv('OPENAI_MODEL') or 'gpt-4o-mini'
except ImportError:
    print("ERROR: openai package not installed")
    sys.exit(1)

# Fonti dei bandi
BANDI_SOURCES = [
    {
        'name': 'ConcorsiPubblici.com',
        'url': 'https://www.concorsipubblici.com/concorsi/occupazione/pro/avvocato-581',
        'type': 'html'
    },
    {
        'name': 'Concorsi.it',
        'url': 'https://www.concorsi.it/concorsi-pubblici/avvocato',
        'type': 'html'
    },
    {
        'name': 'Ministero Giustizia',
        'url': 'https://www.giustizia.it/giustizia/page/it/concorsi_esami_selezioni_assunzioni',
        'type': 'html'
    }
]

def fetch_bandi_from_source(source):
    """Scarica i bandi da una fonte specifica"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(source['url'], headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Error fetching {source['name']}: HTTP {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        bandi = []
        
        # Parser per ConcorsiPubblici.com
        if 'concorsipubblici.com' in source['url']:
            bandi_elements = soup.find_all('div', class_=['concorso-item', 'job-item'])
            for elem in bandi_elements[:10]:
                try:
                    title = elem.find(['h2', 'h3', 'a'])
                    if title:
                        bandi.append({
                            'source': source['name'],
                            'title': title.get_text(strip=True),
                            'url': source['url'],
                            'found_date': datetime.now().strftime('%Y-%m-%d')
                        })
                except:
                    continue
        
        # Parser per Concorsi.it
        elif 'concorsi.it' in source['url']:
            links = soup.find_all('a', href=re.compile(r'/concorsi-pubblici/'))
            for link in links[:10]:
                text = link.get_text(strip=True)
                if 'avvocato' in text.lower() and len(text) > 20:
                    bandi.append({
                        'source': source['name'],
                        'title': text,
                        'url': 'https://www.concorsi.it' + link['href'] if link['href'].startswith('/') else link['href'],
                        'found_date': datetime.now().strftime('%Y-%m-%d')
                    })
        
        # Parser generico
        else:
            links = soup.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                if ('avvocato' in text.lower() or 'legale' in text.lower()) and len(text) > 30 and len(text) < 300:
                    if 'bando' in text.lower() or 'concorso' in text.lower() or 'selezione' in text.lower():
                        bandi.append({
                            'source': source['name'],
                            'title': text,
                            'url': link['href'] if link['href'].startswith('http') else source['url'],
                            'found_date': datetime.now().strftime('%Y-%m-%d')
                        })
        
        print(f"  Trovati {len(bandi)} bandi da {source['name']}")
        return bandi[:5]  # Limita a 5 per fonte
        
    except Exception as e:
        print(f"Error scraping {source['name']}: {e}")
        return []

def filter_bandi_with_openai(all_bandi):
    """Filtra i bandi usando OpenAI per trovare solo quelli per avvocati libero foro (collaboratori)"""
    if not all_bandi:
        return []
    
    # Prepara il testo dei bandi
    bandi_text = "\n\n".join([f"{i+1}. {b['title']} (Fonte: {b['source']})" for i, b in enumerate(all_bandi)])
    
    prompt = f"""Analizza questi bandi e identifica SOLO quelli che cercano avvocati come COLLABORATORI/CONSULENTI/LIBERO FORO (NON dipendenti a tempo indeterminato).

Criteri per includere un bando:
- Deve cercare avvocati come collaboratori, consulenti esterni, libero foro
- Deve essere ATTIVO (non scaduto)
- NO assunzioni a tempo indeterminato come dipendenti
- NO concorsi pubblici per ruoli dirigenziali interni

Bandi da analizzare:
{bandi_text}

Rispondi SOLO con un JSON array contenente i numeri dei bandi pertinenti, esempio: [1, 3, 5]
Se nessun bando è pertinente, rispondi: []"""
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': 'Sei un esperto di bandi pubblici per avvocati. Rispondi sempre in formato JSON array.'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.2
        )
        
        content = response.choices[0].message.content.strip()
        # Estrai JSON dalla risposta
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
        if content.endswith('```'):
            content = content.rsplit('```', 1)[0]
        content = content.strip()
        
        selected_indices = json.loads(content)
        filtered_bandi = [all_bandi[i-1] for i in selected_indices if 0 < i <= len(all_bandi)]
        
        print(f"  OpenAI ha filtrato: {len(filtered_bandi)} bandi pertinenti su {len(all_bandi)} totali")
        return filtered_bandi
        
    except Exception as e:
        print(f"Error filtering with OpenAI: {e}")
        # Fallback: filtra manualmente per parole chiave
        keywords = ['collaboratore', 'collaborazione', 'consulente', 'consulenza', 'libero foro', 'esterno', 'professionale']
        filtered = [b for b in all_bandi if any(kw in b['title'].lower() for kw in keywords)]
        return filtered

def send_email_report(bandi_pertinenti, total_found):
    """Invia email con i bandi trovati"""
    sender_email = os.getenv('EMAIL_FROM') or os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('EMAIL_PASSWORD') or os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('EMAIL_TO_LEGAL', 'studiolegaleartax.it')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    if not sender_email or not sender_password:
        print("ERROR: Email credentials not configured")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📋 LegalBandi Report - {datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    if not bandi_pertinenti:
        html_body = f"""<html><body>
<h2>🔍 Monitoraggio Bandi Avvocati - Nessun nuovo bando</h2>
<p><strong>Data scansione:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
<p>Bandi totali analizzati: {total_found}</p>
<p>Bandi pertinenti (collaboratori libero foro): <strong>0</strong></p>
<hr>
<p><em>Nessun nuovo bando per avvocati collaboratori/libero foro trovato questa settimana.</em></p>
<p>Il sistema continuerà a monitorare settimanalmente.</p>
</body></html>"""
    else:
        bandi_html = ""
        for i, bando in enumerate(bandi_pertinenti, 1):
            bandi_html += f"""
<div style="background: #f5f5f5; padding: 15px; margin: 10px 0; border-left: 4px solid #2e7d32;">
    <h3 style="margin: 0 0 10px 0; color: #1976d2;">{i}. {bando['title']}</h3>
    <p style="margin: 5px 0;"><strong>Fonte:</strong> {bando['source']}</p>
    <p style="margin: 5px 0;"><strong>Link:</strong> <a href="{bando['url']}">{bando['url'][:80]}...</a></p>
    <p style="margin: 5px 0; font-size: 12px; color: #666;">Trovato il: {bando['found_date']}</p>
</div>
"""
        
        html_body = f"""<html><body>
<h2 style="color: #2e7d32;">✅ Nuovi Bandi per Avvocati Collaboratori</h2>
<p><strong>Data scansione:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
<p>Bandi totali analizzati: {total_found}</p>
<p>Bandi pertinenti (collaboratori libero foro): <strong>{len(bandi_pertinenti)}</strong></p>
<hr>
{bandi_html}
<hr>
<p style="font-size: 12px; color: #666;"><em>Generato automaticamente da LegalBandi Monitor</em></p>
</body></html>"""
    
    msg.attach(MIMEText(html_body, 'html'))
    
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
    print(f"\n🔍 LegalBandi Monitor - Avvio scansione {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n[1/3] Recupero bandi da fonti online...")
    
    all_bandi = []
    for source in BANDI_SOURCES:
        print(f"  Scansiono: {source['name']}")
        bandi = fetch_bandi_from_source(source)
        all_bandi.extend(bandi)
    
    print(f"\nTotale bandi trovati: {len(all_bandi)}")
    
    if not all_bandi:
        print("\n⚠️ Nessun bando trovato nelle fonti")
        send_email_report([], 0)
        return 0
    
    print("\n[2/3] Filtro bandi con OpenAI (solo collaboratori/libero foro)...")
    bandi_pertinenti = filter_bandi_with_openai(all_bandi)
    
    print(f"\nBandi pertinenti: {len(bandi_pertinenti)}")
    
    print("\n[3/3] Invio report via email...")
    success = send_email_report(bandi_pertinenti, len(all_bandi))
    
    if success:
        print("\n✅ Processo completato con successo")
    else:
        print("\n⚠️ Email non inviata (credenziali non configurate)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
