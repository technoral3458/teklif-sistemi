import os
import datetime
import base64

class PreviewEngine:
    @staticmethod
    def get_image_base64(img_path):
        if not img_path or not os.path.exists(img_path): return ""
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(img_path)[1].lower().replace('.', '')
            return f"data:image/{ext if ext else 'png'};base64,{b64}"
        except: return ""

    @staticmethod
    def generate_html(customer, model, base_price, machine_img, specs, selected_options, conditions=None, delivery_type=""):
        tarih = datetime.datetime.now().strftime("%d.%m.%Y")
        m_qty = conditions.get("machine_qty", 1)
        agreed_price = conditions.get("agreed_price", 0)
        
        m_img_b64 = PreviewEngine.get_image_base64(machine_img)
        logo_b64 = "" # Eğer logo varsa buraya ekleyebilirsiniz

        # CSS - PDF ve Web uyumlu
        css = """
            body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 12px; color: #333; }
            .header { border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-bottom: 20px; }
            .section-title { background: #1e293b; color: white; padding: 5px 10px; font-weight: bold; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
            .price-box { background: #f8fafc; border-left: 5px solid #e67e22; padding: 15px; text-align: right; margin-top: 20px; }
            .total-price { font-size: 24px; font-weight: bold; color: #e67e22; }
        """

        html = f"""
        <html>
        <head><style>{css}</style></head>
        <body>
            <div class="header">
                <table width="100%">
                    <tr>
                        <td><h2 style="margin:0;">ERSAN MAKİNE</h2></td>
                        <td align="right">Tarih: {tarih}<br>Teklif No: TR-{datetime.datetime.now().strftime("%y%m%d")}</td>
                    </tr>
                </table>
            </div>

            <div style="text-align:center;">
                <img src="{m_img_b64}" style="max-height:250px;"><br>
                <h2 style="margin:10px 0;">MODEL: {model}</h2>
                <p>Sayın Yetkili: <b>{customer}</b></p>
            </div>

            <div class="section-title">🔍 MAKİNE ÖZELLİKLERİ VE DONANIMLAR</div>
            <table>
                <tr style="background:#f1f5f9;">
                    <th>Açıklama</th>
                    <th align="center">Adet</th>
                    <th align="right">Tutar</th>
                </tr>
                <tr>
                    <td>{model} (Standart Donanım)</td>
                    <td align="center">{m_qty}</td>
                    <td align="right">{base_price*m_qty:,.2f}</td>
                </tr>
        """
        
        for opt in selected_options:
            html += f"""
                <tr>
                    <td style="color:#10b981;">+ {opt['n']}</td>
                    <td align="center">{opt['q']}</td>
                    <td align="right">{(opt['p']*opt['q']):,.2f}</td>
                </tr>
            """

        html += f"""
            </table>

            <div class="price-box">
                <div style="font-size:14px; color:#64748b;">Teslimat: {delivery_type}</div>
                <div style="margin-top:10px;">TOPLAM NET TUTAR (KDV Hariç)</div>
                <div class="total-price">{agreed_price:,.2f}</div>
            </div>
            
            <div style="margin-top:30px; font-size:10px; color:#999; text-align:center;">
                Ersan Makine San. ve Tic. Ltd. Şti. | www.ersanmakina.net
            </div>
        </body>
        </html>
        """
        return html
