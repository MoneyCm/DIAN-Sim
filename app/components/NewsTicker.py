import streamlit as st
import datetime

def render_news_ticker():
    """renders a scrolling news ticker with regulatory updates."""
    
    # In a real app, this would come from a database or API
    alerts = [
        {"date": "2026-01-15", "tag": "REFORMA", "text": "Ley 3450 de 2025 modifica tarifas del Régimen Simple. Actualizando base de preguntas..."},
        {"date": "2026-01-20", "tag": "ADUANAS", "text": "Nueva Resolución 004 establece control biométrico en zonas francas."},
        {"date": "2026-02-01", "tag": "SISTEMAS", "text": "Mantenimiento programado del MUISCA este fin de semana."}
    ]
    
    # CSS for the ticker
    st.markdown("""
    <style>
        .ticker-wrap {
            width: 100%;
            background-color: #2c3e50;
            color: white;
            padding: 10px;
            overflow: hidden;
            white-space: nowrap;
            box-sizing: border-box;
            border-bottom: 3px solid #e74c3c;
        }
        .ticker {
            display: inline-block;
            padding-left: 100%;
            animation: ticker 30s linear infinite;
        }
        .ticker-item {
            display: inline-block;
            padding: 0 2rem;
            font-size: 0.9rem;
            font-family: monospace;
        }
        .ticker-tag {
            background-color: #e74c3c;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: bold;
            margin-right: 5px;
            font-size: 0.75rem;
        }
        
        @keyframes ticker {
            0% { transform: translate3d(0, 0, 0); }
            100% { transform: translate3d(-100%, 0, 0); }
        }
        
        /* Stop animation on hover */
        .ticker-wrap:hover .ticker {
            animation-play-state: paused;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # HTML Structure
    ticker_items = ""
    for alert in alerts:
        ticker_items += f'<div class="ticker-item"><span class="ticker-tag">{alert["tag"]}</span> {alert["date"]}: {alert["text"]}</div>'
        
    st.markdown(f"""
    <div class="ticker-wrap">
        <div class="ticker">
            {ticker_items}
        </div>
    </div>
    """, unsafe_allow_html=True)
