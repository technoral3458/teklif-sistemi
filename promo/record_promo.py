"""Teklif sistemi tanıtım videosu — gerçek arayüzün ekran kaydı.

Kullanım:
    python3 record_promo.py <taban_url> <kullanici> <sifre> <cikti_klasoru>

Kendi sunucunuzda kendi verinizle çalıştırırsanız video sizin
makineleriniz ve logonuzla oluşur.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899"
USER = sys.argv[2] if len(sys.argv) > 2 else "admin@example.com"
PASS = sys.argv[3] if len(sys.argv) > 3 else "Admin123!"
OUT = sys.argv[4] if len(sys.argv) > 4 else "/tmp/promo"
PJOB = sys.argv[5] if len(sys.argv) > 5 else ""
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
VW, VH = 1600, 900

# ── Sayfaya enjekte edilen katman: imleç + altyazı + kart ────────────────────
OVERLAY = r"""
(() => {
  let built = false;
  function build() {
    if (built || !document.documentElement) return built;
    built = true;
  const css = document.createElement('style');
  css.textContent = `
    #pz-cur{position:fixed;z-index:2147483647;width:22px;height:22px;margin:-11px 0 0 -11px;
      border-radius:50%;background:rgba(255,255,255,.22);border:2px solid #fff;
      box-shadow:0 0 0 2px rgba(0,0,0,.35),0 3px 14px rgba(0,0,0,.5);
      pointer-events:none;transition:transform .09s ease;left:-99px;top:-99px}
    #pz-cur.dn{transform:scale(.68);background:rgba(255,255,255,.5)}
    .pz-rip{position:fixed;z-index:2147483646;width:14px;height:14px;margin:-7px 0 0 -7px;
      border-radius:50%;border:2.5px solid #4da3ff;pointer-events:none;
      animation:pzr .62s ease-out forwards}
    @keyframes pzr{to{width:88px;height:88px;margin:-44px 0 0 -44px;opacity:0;border-width:1px}}
    #pz-cap{position:fixed;left:0;right:0;bottom:0;z-index:2147483645;pointer-events:none;
      padding:30px 56px 34px;color:#fff;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
      background:linear-gradient(to top,rgba(5,9,16,.93) 0%,rgba(5,9,16,.80) 55%,rgba(5,9,16,0) 100%);
      opacity:0;transform:translateY(24px);transition:opacity .42s ease,transform .42s ease}
    #pz-cap.on{opacity:1;transform:translateY(0)}
    #pz-cap .n{display:inline-block;background:#2f81f7;color:#fff;font-size:15px;font-weight:800;
      width:32px;height:32px;line-height:32px;text-align:center;border-radius:9px;margin-right:13px;
      vertical-align:middle}
    #pz-cap .t{display:inline;font-size:33px;font-weight:800;letter-spacing:-.4px;
      vertical-align:middle;text-shadow:0 2px 16px rgba(0,0,0,.8)}
    #pz-cap .s{margin:11px 0 0 0;font-size:19px;font-weight:500;color:#c6d4e4;
      text-shadow:0 2px 12px rgba(0,0,0,.8)}
    #pz-card{position:fixed;inset:0;z-index:2147483647;display:none;color:#fff;
      font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
      background:radial-gradient(1100px 620px at 50% 36%,#15335c 0%,#0a1322 62%,#05080f 100%);
      flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:60px}
    #pz-card.on{display:flex}
    #pz-card .k{font-size:15px;font-weight:700;letter-spacing:4.5px;color:#5fa8ff;
      text-transform:uppercase;opacity:0;animation:pzu .7s .1s ease forwards}
    #pz-card h1{font-size:72px;font-weight:900;letter-spacing:-2.2px;margin:18px 0 0;
      line-height:1.04;opacity:0;animation:pzu .7s .28s ease forwards}
    #pz-card h2{font-size:27px;font-weight:500;color:#aec4dd;margin:22px 0 0;max-width:1000px;
      line-height:1.45;opacity:0;animation:pzu .7s .5s ease forwards}
    #pz-card .row{display:flex;gap:16px;margin-top:46px;flex-wrap:wrap;justify-content:center;
      opacity:0;animation:pzu .7s .72s ease forwards}
    #pz-card .chip{background:rgba(47,129,247,.14);border:1.5px solid rgba(47,129,247,.5);
      border-radius:999px;padding:13px 26px;font-size:19px;font-weight:600;color:#dce9f8}
    @keyframes pzu{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}
  `;
  document.documentElement.appendChild(css);
  const mk = (id, html) => { const e = document.createElement('div'); e.id = id;
    if (html) e.innerHTML = html; document.documentElement.appendChild(e); return e; };
  const cur = mk('pz-cur'), cap = mk('pz-cap', '<div><span class="n" style="display:none"></span><span class="t"></span></div><p class="s"></p>');
  mk('pz-card', '<div class="k"></div><h1></h1><h2></h2><div class="row"></div>');

  addEventListener('mousemove', e => { cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', e => {
    cur.classList.add('dn');
    const r = document.createElement('div'); r.className = 'pz-rip';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    document.documentElement.appendChild(r); setTimeout(() => r.remove(), 640);
  }, true);
  addEventListener('mouseup', () => cur.classList.remove('dn'), true);

    return true;
  }

  const ready = () => build() && document.getElementById('pz-cap');
  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', build);
  else build();

  window.__say = (t, s, n) => {
    if (!ready()) return;
    const c = document.getElementById('pz-cap');
    c.querySelector('.t').textContent = t;
    c.querySelector('.s').textContent = s || '';
    const nn = c.querySelector('.n');
    if (n) { nn.textContent = n; nn.style.display = 'inline-block'; } else { nn.style.display = 'none'; }
    c.classList.add('on');
  };
  window.__quiet = () => { if (ready()) document.getElementById('pz-cap').classList.remove('on'); };
  window.__card = (kicker, h1, h2, chips) => {
    if (!ready()) return;
    const c = document.getElementById('pz-card');
    c.querySelector('.k').textContent = kicker;
    c.querySelector('h1').textContent = h1;
    c.querySelector('h2').textContent = h2 || '';
    c.querySelector('.row').innerHTML = (chips || []).map(x => `<div class="chip">${x}</div>`).join('');
    c.className = ''; void c.offsetWidth; c.className = 'on';
    document.getElementById('pz-cur').style.display = 'none';
  };
  window.__uncard = () => {
    if (!ready()) return;
    document.getElementById('pz-card').className = '';
    document.getElementById('pz-cur').style.display = '';
  };
})();
"""


class Director:
    def __init__(self, page):
        self.p = page
        self.x, self.y = VW / 2, VH / 2

    async def hold(self, ms):
        await self.p.wait_for_timeout(ms)

    async def say(self, t, s="", n=None, ms=0):
        await self.p.wait_for_function("()=>!!window.__say")
        await self.p.evaluate("a=>window.__say(a[0],a[1],a[2])", [t, s, n])
        if ms:
            await self.hold(ms)

    async def quiet(self):
        await self.p.evaluate("()=>window.__quiet&&window.__quiet()")

    async def card(self, kicker, h1, h2="", chips=None, ms=3400):
        await self.p.wait_for_function("()=>!!window.__card")
        await self.p.evaluate("a=>window.__card(a[0],a[1],a[2],a[3])",
                              [kicker, h1, h2, chips or []])
        await self.hold(ms)
        await self.p.evaluate("()=>window.__uncard()")

    async def to(self, sel, dur=620):
        """İmleci hedefin ortasına yumuşakça taşı."""
        el = await self.p.query_selector(sel)
        if not el:
            return None
        try:
            await el.scroll_into_view_if_needed()
        except Exception:
            pass
        await self.hold(260)
        b = await el.bounding_box()
        if not b:
            return None
        tx, ty = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        await self.p.mouse.move(tx, ty, steps=max(14, int(dur / 22)))
        self.x, self.y = tx, ty
        await self.hold(170)
        return el

    async def click(self, sel, after=520):
        el = await self.to(sel)
        if not el:
            return False
        await self.p.mouse.down(); await self.hold(70); await self.p.mouse.up()
        await self.hold(after)
        return True

    async def type_in(self, sel, text, delay=58):
        await self.to(sel)
        await self.p.click(sel)
        await self.p.fill(sel, "")
        await self.p.type(sel, text, delay=delay)
        await self.hold(220)

    async def scroll(self, dy, steps=22, ms=26):
        for _ in range(steps):
            await self.p.mouse.wheel(0, dy / steps)
            await self.hold(ms)

    async def goto(self, path):
        await self.p.goto(BASE + path, wait_until="networkidle")
        await self.hold(420)


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as pw:
        br = await pw.chromium.launch(executable_path=CHROME,
                                      args=["--force-device-scale-factor=1"])
        ctx = await br.new_context(viewport={"width": VW, "height": VH},
                                   record_video_dir=OUT,
                                   record_video_size={"width": VW, "height": VH},
                                   locale="tr-TR")
        await ctx.add_init_script(OVERLAY)
        pg = await ctx.new_page()
        d = Director(pg)

        # ══ AÇILIŞ ══
        await pg.goto(BASE + "/login", wait_until="networkidle")
        await d.card("B2B Teklif Sistemi", "Teklif hazırlamak\nartık dakikalar sürüyor",
                     "Makine satışınızın tamamı tek panelde",
                     ["Hızlı teklif", "Otomatik PDF", "Müşteri self-servis"], 4200)

        # ══ 1 · GİRİŞ ══
        await d.say("Panele girin", "Bayileriniz ve üreticileriniz de aynı sistemde", "1")
        await d.hold(900)
        await d.type_in("input[name=email]", USER, 42)
        await d.type_in("input[name=password]", PASS, 42)
        await d.click("button[type=submit]", 1500)
        await pg.wait_for_load_state("networkidle")

        # ══ 2 · TEKLİF SİHİRBAZI ══
        await d.goto("/offers/new")
        await d.say("Müşteriyi seçin", "Kayıtlı müşteri ya da anında yeni kayıt", "2")
        await d.hold(1100)
        await d.to("#wCustomerId")
        await pg.select_option("#wCustomerId", index=1)
        await d.hold(1000)
        await d.click("#wstep1 button.btn-primary", 900)

        await d.say("Makineyi seçin", "Fiyatlar listede, arama yok, hesap yok", "3")
        await d.hold(1400)
        await d.scroll(260, 14, 22)
        await d.hold(700)
        await d.click(".model-card", 1200)
        await d.quiet()
        await d.hold(500)
        await d.click("#wstep2 button.btn-primary", 1000)

        await d.say("Opsiyonları işaretleyin", "Toplam tutar anında güncellenir", "4")
        await d.hold(1100)
        for sel in [".option-row:nth-of-type(1) input[type=checkbox]",
                    ".option-row:nth-of-type(2) input[type=checkbox]",
                    ".option-row:nth-of-type(4) input[type=checkbox]"]:
            await d.click(sel, 780)
        await d.hold(1100)
        await d.click("#wstep3 button.btn-primary", 1000)

        await d.say("Teslim ve ödeme", "Son adım — ve teklif hazır", "5")
        await d.hold(900)
        await d.type_in("#wDeliveryTime", "90 gün", 62)
        await d.type_in("#wDeliveryMethod", "Alıcı fabrikasına teslim", 32)
        await d.hold(700)
        await d.quiet()
        await d.click("#wstep4 button[type=submit]", 2600)
        await pg.wait_for_load_state("networkidle")

        # ══ 3 · TEKLİF HAZIR ══
        await d.say("Teklif hazır", "Baştan sona bir dakikadan kısa", "✓")
        await d.hold(2200)
        await d.scroll(420, 20, 26)
        await d.hold(1500)
        await d.scroll(-420, 16, 20)
        await d.quiet()
        await d.hold(500)

        # ══ 4 · BELGELER ══
        await d.say("Tek tıkla profesyonel belgeler",
                    "Teklif PDF · Ürün kataloğu · Teknik özellikler · Instagram görseli")
        await d.hold(1300)
        for sel in ['a[href$="/pdf-view"]', 'a[href$="/catalog-pdf"]',
                    'a[href$="/teknik-pdf"]', 'a[href$="/social-card"]']:
            await d.to(sel, 460)
            await d.hold(620)
        await d.hold(700)
        await d.quiet()

        # ══ 5 · MÜŞTERİ SELF-SERVİS ══
        await d.goto("/teklif-al")
        await d.say("Müşteriniz kendi makinesini kursun",
                    "Üyelik yok — talep doğrudan panelinize düşer", "+")
        await d.hold(1900)
        await d.scroll(300, 14, 24)
        await d.hold(900)
        try:
            await d.click(".pq-model-card", 900)
            await d.click("#pqStep1Next", 1800)
            await d.say("Seçenekleri kendisi işaretler",
                        "Fiyat görünmez — talep size gelir", "+")
            await d.hold(1900)
            await d.scroll(300, 14, 24)
            await d.hold(1300)
        except Exception:
            await d.hold(1200)
        await d.quiet()

        # ══ 6 · SERVİS TALEBİ ══
        await d.goto("/servis-talebi")
        await d.say("Arıza bildirimi de burada",
                    "Müşteri fotoğrafıyla bildirir, panelde takip edersiniz", "+")
        await d.hold(2000)
        await d.scroll(340, 16, 24)
        await d.hold(1600)
        await d.quiet()

        # ══ 7 · PARAMETRİK KESİM (3B) ══
        if PJOB:
            await d.goto(f"/parametric/{PJOB}")
            await d.say("Ve dahası: parametrik kesim",
                        "Resimden 3B panele, CNC'ye hazır DXF çıktısı", "+")
            await d.hold(2400)
            box = await pg.query_selector("#p3dCanvas")
            if box:
                b = await box.bounding_box()
                cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
                await pg.mouse.move(cx, cy, steps=14)
                await pg.mouse.down()
                for i in range(46):                       # fareyle döndürme
                    await pg.mouse.move(cx + i * 7, cy - i * 1.6, steps=1)
                    await d.hold(26)
                await pg.mouse.up()
                await d.hold(1500)
            await d.quiet()
            await d.hold(400)

        # ══ KAPANIŞ ══
        await d.card("Tek panel, tüm süreç",
                     "Daha hızlı teklif,\ndaha çok satış",
                     "Teklif · Sipariş · Üretim takibi · Cari · Servis",
                     ["Dakikalar içinde teklif", "Otomatik belgeler",
                      "7/24 müşteri self-servis"], 4800)

        await ctx.close()
        await br.close()
    print("kayıt tamam →", OUT)


asyncio.run(main())
