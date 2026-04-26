import os
import sys
import json
import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtPrintSupport import QPrinter

import language as lang
import database

class PreviewEngine:
    @staticmethod
    def get_real_path(img_name):
        if not img_name: 
            return None
        base_dir = os.getcwd() 
        candidates = [
            img_name, 
            os.path.join(base_dir, img_name), 
            os.path.join(base_dir, "images", os.path.basename(img_name)),
            os.path.join(os.path.dirname(__file__), "images", os.path.basename(img_name))
        ]
        for path in candidates:
            if os.path.exists(path): return os.path.abspath(path).replace("\\", "/")
        return None

    @staticmethod
    def generate_html(customer, model, base_price, machine_img, specs, selected_options, conditions=None, delivery_type="Gümrük İşlemleri Yapılmış Antrepo Teslim", gallery_images=""):
        tarih = datetime.datetime.now().strftime("%d.%m.%Y")
        
        m_symbol = "$"
        try:
            res_m = database.get_query("SELECT currency FROM models WHERE name=?", (model.strip(),))
            if res_m and res_m[0][0]: m_symbol = lang.get_symbol_by_code(res_m[0][0])
        except: pass

        try:
            res = database.get_query("SELECT company_name, logo_path, website, footer_text FROM company_profile WHERE id=1")
            if res: comp_name, comp_logo, comp_web, comp_footer = res[0]
            else: comp_name, comp_logo, comp_web, comp_footer = "ERSAN MAKİNE", "", "www.ersanmakine.com", "Ersan Makine San. ve Tic. Ltd. Şti."
        except:
            comp_name, comp_logo, comp_web, comp_footer = "ERSAN MAKİNE", "", "www.ersanmakine.com", "Ersan Makine San. ve Tic. Ltd. Şti."

        machine_qty = conditions.get("machine_qty", 1) if conditions else 1
        hide_specs = conditions.get("hide_specs", False) if conditions else False

        real_logo = PreviewEngine.get_real_path(comp_logo)
        header_logo_html = f'<img src="file:///{real_logo}" style="max-height:60px;">' if real_logo else f'<div style="font-size:24px; font-weight:900; color:#2c3e50;">{comp_name}</div>'

        # HER SAYFANIN BAŞINDAKİ ANTET VE LOGO
        page_header = f"""
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 10px; border-bottom: 2px solid #e67e22; padding-bottom: 5px;">
            <tr>
                <td align="left" valign="middle" width="50%">
                    {header_logo_html}
                </td>
                <td align="right" valign="middle" width="50%" style="color: #64748b; font-size: 11px;">
                    {comp_web}<br>{comp_footer}
                </td>
            </tr>
        </table>
        """
        
        real_m_img = PreviewEngine.get_real_path(machine_img)
        m_img_html = f'<img src="file:///{real_m_img}" style="max-width:100%; max-height:350px; object-fit:contain; margin: 10px 0;">' if real_m_img else f'<div style="padding:40px; text-align:center; color:#94a3b8; border:1px dashed #cbd5e1; margin:10px 0;">{lang.tr("Makine Görseli Yok")}</div>'

        css = """
            body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #ffffff; margin: 0; padding: 0; color: #1e293b; font-size: 13px; }
            .thumb { max-width: 140px; max-height: 90px; border-radius: 6px; border: 1px solid #e2e8f0; object-fit: cover; }
            h3 { background-color: #1e293b; color: white; padding: 8px 15px; font-size: 15px; border-radius: 4px; margin-top: 0; margin-bottom: 10px; }
            .price-box { border-left: 8px solid #e67e22; background-color: #f8fafc; padding: 25px; text-align: right; margin-top: 20px; border-radius: 8px; }
        """

        # ORAN SÜTUNU TAMAMEN KALDIRILDI
        payment_html = ""
        payment_plan = conditions.get('payment_plan', []) if conditions else []
        if payment_plan:
            payment_html = f"""
            <table style="width: 100%; border-collapse: collapse; margin: 0; padding: 0;">
                <tr>
                    <th width="60%" style="border-bottom: 1px solid #e2e8f0; padding: 8px 0; text-align: left; color: #475569;">{lang.tr("Açıklama / Vade")}</th>
                    <th width="40%" align="right" style="border-bottom: 1px solid #e2e8f0; padding: 8px 0; text-align: right; color: #475569;">{lang.tr("Tutar")}</th>
                </tr>
            """
            for row in payment_plan:
                amt_display = f"{row[2]} {m_symbol}" if len(row) > 2 and str(row[2]).strip() else "-"
                payment_html += f"<tr><td style='padding:8px 0; border-bottom:1px dashed #f1f5f9;'>{row[0]}</td><td align='right' style='padding:8px 0; border-bottom:1px dashed #f1f5f9; text-align: right;'><b>{amt_display}</b></td></tr>"
            payment_html += '</table>'
        else:
            payment_html = f"<i>{lang.tr('Belirtilmedi')}</i>"

        subtotal_calculated = conditions.get('subtotal_calculated', float(base_price) * machine_qty) if conditions else (float(base_price) * machine_qty)
        discount_pct = conditions.get('discount_pct', 0.0) if conditions else 0.0
        agreed_price = conditions.get('agreed_price', subtotal_calculated) if conditions else subtotal_calculated
        
        if machine_qty > 1: base_price_display = f'{float(base_price):,.2f} {m_symbol} x {machine_qty} {lang.tr("Adet")} = {float(base_price) * machine_qty:,.2f} {m_symbol}'
        else: base_price_display = f'{float(base_price):,.2f} {m_symbol}'

        if discount_pct > 0:
            price_summary_html = f"""
            <div class="price-box">
                <div style="font-size: 15px; color: #64748b; font-weight: 600;">{lang.tr("Makine Baz Fiyatı:")} {base_price_display}</div>
                <div style="margin-top:10px; font-size: 15px; color: #94a3b8;">{lang.tr("Sistem Liste Toplamı:")} <span style="text-decoration: line-through;">{subtotal_calculated:,.2f} {m_symbol}</span></div>
                <div style="font-size: 15px; color: #ef4444; font-weight: bold; margin-top:5px;">{lang.tr("Uygulanan Özel İskonto:")} %{discount_pct:,.2f}</div>
                <div style="font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 15px;">{lang.tr("NET FİYAT (KDV Hariç)")}</div>
                <div style="font-size: 42px; font-weight: 900; color: #e67e22; margin-top: 5px;">{agreed_price:,.2f} {m_symbol}</div>
            </div>
            """
        else:
            price_summary_html = f"""
            <div class="price-box">
                <div style="font-size: 15px; color: #64748b; font-weight: 600;">{lang.tr("Makine Baz Fiyatı:")} {base_price_display}</div>
                <div style="font-size: 18px; font-weight: bold; color: #0f172a; margin-top: 15px;">{lang.tr("GENEL TOPLAM (KDV Hariç)")}</div>
                <div style="font-size: 42px; font-weight: 900; color: #e67e22; margin-top: 5px;">{agreed_price:,.2f} {m_symbol}</div>
            </div>
            """

        cond_html = ""
        if conditions:
            bank_info = conditions.get('bank', '').replace('\n', '<br>')
            notes_info = conditions.get('notes', '').replace('\n', '<br>')
            cond_html = f"""
            <div style="margin-top: 30px;">
                <h4 style="margin-top: 0; color: #0f172a; border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-bottom: 10px; font-size: 16px;">📝 {lang.tr("SATIŞ VE TESLİMAT ŞARTLARI")}</h4>
                <table width="100%" style="border-collapse: collapse;">
                    <tr>
                        <td width="200" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>{lang.tr("Teslimat Şekli:")}</b></td>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; color:#e67e22; font-weight:bold; font-size: 14px;">{delivery_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>{lang.tr("Teslim Süresi:")}</b></td>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{conditions.get('delivery_time', '')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>{lang.tr("Nakliye / Lojistik:")}</b></td>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{conditions.get('shipping', '')}</td>
                    </tr>
                    <tr>
                        <td valign="top" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>{lang.tr("Ödeme Planı:")}</b></td>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1;">{payment_html}</td>
                    </tr>
                    <tr>
                        <td valign="top" style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;"><b>{lang.tr("Banka Bilgileri:")}</b></td>
                        <td style="padding: 12px 0; border-bottom: 1px solid #cbd5e1; font-size: 14px;">{bank_info}</td>
                    </tr>
                </table>
            """
            if notes_info.strip():
                cond_html += f'<div style="margin-top:15px; padding-top:15px; font-size:13px; color:#475569;"><b>{lang.tr("Özel Notlar:")}</b><br>{notes_info}</div>'
            cond_html += "</div>"

        pages = []
        qty_title_addon = f' <span style="color:#e67e22;">(x{machine_qty} {lang.tr("Adet")})</span>' if machine_qty > 1 else ""

        # =========================================================
        # SAYFA 1: KAPAK
        # =========================================================
        page1 = f"""
        <div>
            {page_header}
            <div style="text-align:center; margin-top:20px;">
                {m_img_html}
                <div style="font-size: 32px; font-weight: 800; margin: 20px 0; color: #0f172a;">{lang.tr("MODEL:")} {model}{qty_title_addon}</div>
            </div>
            <table width="100%" cellpadding="15" style="border: 1px solid #e2e8f0; background-color: #f8fafc; border-radius: 8px; margin-top: 30px; border-collapse: collapse;">
                <tr><td width="150" style="color:#64748b; border-bottom:1px solid #e2e8f0;">{lang.tr("Sayın Yetkili:")}</td><td style="font-size:18px; font-weight:bold; border-bottom:1px solid #e2e8f0;">{customer}</td></tr>
                <tr><td style="color:#64748b; border-bottom:1px solid #e2e8f0;">{lang.tr("Tarih:")}</td><td style="border-bottom:1px solid #e2e8f0;">{tarih}</td></tr>
                <tr><td style="color:#64748b;">{lang.tr("Teklif No:")}</td><td style="font-weight:bold;">TR-{datetime.datetime.now().strftime("%y%m%d")}</td></tr>
            </table>
        </div>
        """
        pages.append(page1)

        # =========================================================
        # SAYFA 2+: STANDART ÖZELLİKLER (Tam 5 Adet)
        # =========================================================
        if not hide_specs and specs:
            specs_list = [item for item in specs.split("||") if item.strip()]
            chunk_size = 5 
            for i in range(0, len(specs_list), chunk_size):
                chunk = specs_list[i:i + chunk_size]
                devam_txt = f" <span style='font-size:12px; font-weight:normal;'>({lang.tr('Devamı')} {i//chunk_size + 1})</span>" if i > 0 else ""
                
                spec_page = f"""
                <div>
                    {page_header}
                    <h3>🔍 {lang.tr("MAKİNE STANDART ÖZELLİKLERİ")}{devam_txt}</h3>
                """
                for item in chunk:
                    parts = item.split("|")
                    title = parts[0].strip()
                    if len(parts) >= 3:
                        img_name = parts[-1].strip()
                        desc = "|".join(parts[1:-1]).strip()
                    elif len(parts) == 2:
                        img_name = ""
                        desc = parts[1].strip()
                    else:
                        img_name = ""
                        desc = ""
                    
                    desc = desc.replace("\n", "<br>")
                    img_path = PreviewEngine.get_real_path(img_name)
                    img_t = f'<img src="file:///{img_path}" class="thumb">' if img_path else ''
                    
                    spec_page += f"""
                    <table width="100%" style="border-collapse: collapse; page-break-inside: avoid; margin-bottom: 0;">
                        <tr>
                            <td width="20%" align="center" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">{img_t}</td>
                            <td width="80%" align="left" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">
                                <b style="font-size:15px; color:#0f172a;">{title}</b><br>
                                <div style='color:#64748b; font-size:13px; margin-top:4px;'>{desc}</div>
                            </td>
                        </tr>
                    </table>
                    """
                spec_page += "</div>"
                pages.append(spec_page)

        # =========================================================
        # SAYFA X+: OPSİYONLAR (Tam 5 Adet)
        # =========================================================
        if selected_options:
            chunk_size = 5
            for i in range(0, len(selected_options), chunk_size):
                chunk = selected_options[i:i + chunk_size]
                devam_txt = f" <span style='font-size:12px; font-weight:normal;'>({lang.tr('Devamı')} {i//chunk_size + 1})</span>" if i > 0 else ""
                
                opt_page = f"""
                <div>
                    {page_header}
                    <h3>📦 {lang.tr("SEÇİLEN OPSİYONLAR")}{devam_txt}</h3>
                    <table width="100%" style="border-collapse: collapse; background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; margin-bottom: 0;">
                        <tr>
                            <th width="20%" align="center" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: center;">{lang.tr("Görsel")}</th>
                            <th width="55%" align="left" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: left;">{lang.tr("Donanım Açıklaması")}</th>
                            <th width="25%" align="right" style="padding: 10px; font-weight: bold; color: #475569; font-size: 14px; text-align: right;">{lang.tr("Fiyat")}</th>
                        </tr>
                    </table>
                """
                for opt in chunk:
                    img_t = f'<img src="file:///{PreviewEngine.get_real_path(opt["i"])}" class="thumb">' if opt["i"] else ''
                    qty = int(opt.get('q', 1))
                    unit_p = float(opt['p'])
                    sym = opt.get('s', '$')
                    qty_badge = f" <span style='color:#e67e22; font-size:12px; font-weight:bold;'>({qty} {lang.tr('Adet')})</span>" if qty > 1 else ""
                    
                    if qty > 1: 
                        price_display = f"<span style='font-size:11px; color:#94a3b8; font-weight:normal;'>{qty} x {unit_p:,.2f} {sym}</span><br>{unit_p * qty:,.2f} {sym}"
                    else: 
                        price_display = f"{unit_p * qty:,.2f} {sym}"
                    
                    desc = opt['d'].replace('\n', '<br>')
                    
                    opt_page += f"""
                    <table width="100%" style="border-collapse: collapse; page-break-inside: avoid; margin-bottom: 0;">
                        <tr>
                            <td width="20%" align="center" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">{img_t}</td>
                            <td width="55%" align="left" style="padding: 10px; border-bottom: 1px solid #f1f5f9; vertical-align: middle;">
                                <b style="font-size:15px; color:#0f172a;">{opt['n']}</b>{qty_badge}<br>
                                <div style='color:#64748b; font-size:13px; margin-top:4px;'>{desc}</div>
                            </td>
                            <td width="25%" align="right" valign="middle" style="padding: 10px; border-bottom: 1px solid #f1f5f9; font-weight: bold; font-size: 14px; color: #e67e22; text-align: right;">
                                {price_display}
                            </td>
                        </tr>
                    </table>
                    """
                opt_page += "</div>"
                pages.append(opt_page)

        # =========================================================
        # SON SAYFA: FİNAL VE ŞARTLAR (A4'e Sığan Sabit Yükseklik)
        # =========================================================
        final_page = f"""
        <div style="position: relative; height: 260mm;">
            {page_header}
            {price_summary_html}
            {cond_html}
            <div style="position:absolute; bottom:0; width:100%; text-align:center; color:#94a3b8; font-size:12px; padding-top:15px; border-top: 1px solid #f1f5f9;">
                * Bu teklif {tarih} tarihinde oluşturulmuştur.
            </div>
        </div>
        """
        pages.append(final_page)

        # TÜM SAYFALARI BİRLEŞTİR 
        page_separator = '<div style="page-break-before: always; height: 1px; margin: 0; padding: 0;"></div>'
        full_html_content = page_separator.join(pages)

        final_html = f"<!DOCTYPE html><html><head><meta charset='UTF-8'><style>{css}</style></head><body>{full_html_content}</body></html>"
        
        return final_html