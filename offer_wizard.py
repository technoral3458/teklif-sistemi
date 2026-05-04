import streamlit as st
import streamlit.components.v1 as components
import datetime
import pandas as pd
import json
import os
import base64
import sqlite3
import ntpath
import posixpath

# =====================================================================
# VERİTABANI BAĞLANTI MOTORLARI
# =====================================================================
def get_factory(query, params=()):
    conn = sqlite3.connect('factory_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def get_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def exec_sales(query, params=()):
    conn = sqlite3.connect('sales_data.db')
    c = conn.cursor(); c.execute(query, params); conn.commit(); conn.close()

def get_user_query(query, params=()):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor(); c.execute(query, params); res = c.fetchall(); conn.close()
    return res

def init_wizard_tables():
    exec_sales("""CREATE TABLE IF NOT EXISTS offer_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id INTEGER, option_id INTEGER, quantity INTEGER DEFAULT 1)""")
    try:
        of_cols = [c[1] for c in get_sales("PRAGMA table_info(offers)")]
        if "total_price" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN total_price REAL DEFAULT 0.0")
        if "conditions" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN conditions TEXT DEFAULT ''")
        if "status" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN status TEXT DEFAULT 'Beklemede'")
        if "user_id" not in of_cols: exec_sales("ALTER TABLE offers ADD COLUMN user_id INTEGER DEFAULT 1")
    except: pass

# =====================================================================
# GELİŞMİŞ VE AKILLI RESİM OKUMA MOTORU
# =====================================================================
def get_image_base64(path):
    if not path: return ""
    if str(path).startswith("http"): return path
    base_name = posixpath.basename(ntpath.basename(path))
    paths_to_try = [path, f"images/{path}", f"../images/{path}", base_name, f"images/{base_name}"]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    ext = os.path.splitext(p)[1].lower().replace('.', '')
                    if not ext: ext = 'png'
                    return f"data:image/{ext};base64,{base64.b64encode(f.read()).decode()}"
            except: pass
    return ""

def generate_embedded_html(customer, model, base_price, machine_img, specs, selected_options, conditions, m_currency, user_id):
    tarih = datetime.datetime.now().strftime("%d.%m.%Y")
    m_qty = conditions.get("machine_qty", 1)
    agreed_price = conditions.get("agreed_price", 0)
    teklif_no = f"TR-{datetime.datetime.now().strftime('%y%m%d')}"

    try: u_info = get_user_query("SELECT company_name, logo_path, website, address_full, phone FROM users WHERE id=?", (user_id,))[0]
    except: u_info = None
    
    comp_name = u_info[0] if u_info and u_info[0] else "ERSAN MAKİNE"
    comp_logo = u_info[1] if u_info and u_info[1] else ""
    comp_web = u_info[2] if u_info and u_info[2] else "www.ersanmakina.net"
    comp_adr = u_info[3] if u_info and u_info[3] else "Ersan Makine San. Tic. Ltd. Şti."
    comp_tel = u_info[4] if u_info and u_info[4] else ""

    if not comp_logo:
        try: comp_logo = get_factory("SELECT logo_path FROM company_profile WHERE id=1")[0][0]
        except: pass

    logo_b64 = get_image_base64(comp_logo)
    header_logo_html = f'<img src="{logo_b64}" style="max-height:70px; width:auto; object-fit:contain;">' if logo_b64 else f'<div style="font-size:22px; font-weight:900; color:#1e293b;">{comp_name}</div>'

    css = """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        body { font-family: 'Inter', sans-serif; font-size: 14px; color: #1e293b; background: #cbd5e1; margin:0; padding:15px; display: flex; flex-direction: column; align-items: center; }
        .paper { background: #fff; width: 100%; max-width: 850px; min-height: 1120px; padding: 6%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); border-top: 8px solid #2563eb; box-sizing: border-box; overflow: hidden; margin-bottom: 40px; }
        .header { border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
        .section-title { background: #f8fafc; color: #0f172a; padding: 10px 15px; font-weight: 800; font-size: 14px; margin-top: 30px; border-left: 5px solid #2563eb; text-transform: uppercase; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; table-layout: fixed; word-wrap: break-word; }
        th, td { border-bottom: 1px solid #f1f5f9; padding: 12px; text-align: left; vertical-align: middle; }
        .price-box { background: #fffbeb; border: 1px solid #fde68a; padding: 20px; text-align: right; margin-top: 35px; border-radius: 6px; }
        .total-price { font-size: 30px; font-weight: 900; color: #ea580c; word-break: break-all; }
        .elegant-conditions { margin-top: 35px; background: #f8fafc; padding: 20px; border-left: 5px solid #eab308; }
        .print-btn { background: #10b981; color: white; border: none; padding: 15px; font-size: 16px; border-radius: 6px; cursor: pointer; width: 100%; max-width: 850px; margin-bottom: 20px; font-weight: bold; }
        .footer-info { margin-top:30px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:15px; }
        @media print { .no-print { display: none !important; } .paper { box-shadow: none; border: none; padding: 0; margin: 0; width: 100%; max-width: 100%; min-height: auto; } body { background: #fff; padding: 0; } .page-break { page-break-before: always; } }
    """

    page_header_html = f"""
        <div class="header">
            <div>{header_logo_html}</div>
            <div style="text-align:right; font-size: 12px; color: #64748b;"><b>{comp_web}</b><br>Tarih: {tarih}<br>Teklif No: {teklif_no}</div>
        </div>
    """

    html = f"""
    <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><style>{css}</style></head><body>
        <div class="no-print"><button class="print-btn" onclick="window.print()">🖨️ PDF OLARAK KAYDET / YAZDIR</button></div>
        <div class="paper">
            {page_header_html}
            <div style="text-align:center; padding: 15px 0;">
                <img src="{get_image_base64(machine_img)}" style="max-width:100%; max-height:350px; width:auto; height:auto; object-fit:contain; display:block; margin:0 auto;"><br>
                <h2 style="color:#0f172a; margin:15px 0; font-size:24px; font-weight:900;">MODEL: {model}</h2>
                <div style="display:inline-block; background:#f1f5f9; padding: 8px 20px; border-radius: 20px; font-size:15px; color:#475569;">
                    Sayın Yetkili: <b style="color:#0f172a;">{customer}</b>
                </div>
            </div>
    """

    if specs and str(specs).strip():
        html += '<div class="section-title">🔍 MAKİNE STANDART ÖZELLİKLERİ</div><table>'
