/* Dede Modu — imlecin üzerindeki yazıyı büyük bir balonda gösterir.
   Az gören kullanıcılar için; yalnızca ayarlarında açık olan hesaplarda yüklenir. */

(function () {
  'use strict';
  if (window.__senior) return;
  window.__senior = true;

  var OFF_KEY = 'seniorPaused';
  var DELAY = 110;          // imleç durduktan sonra açılma gecikmesi (ms)
  var MAX_CHARS = 420;
  var paused = false;
  try { paused = localStorage.getItem(OFF_KEY) === '1'; } catch (e) {}

  // ── Balon ──────────────────────────────────────────────────────────────
  var css = document.createElement('style');
  css.textContent =
    '#sr-bubble{position:fixed;z-index:2147483000;max-width:640px;pointer-events:none;' +
    'background:#0b1220;color:#fff;border:3px solid var(--accent,#2f81f7);border-radius:16px;' +
    'padding:16px 22px;font-size:31px;line-height:1.38;font-weight:600;letter-spacing:.1px;' +
    'box-shadow:0 18px 60px rgba(0,0,0,.72),0 0 0 1px rgba(255,255,255,.08);' +
    'opacity:0;transform:scale(.96);transition:opacity .1s ease,transform .1s ease;' +
    'word-break:break-word;white-space:pre-wrap;display:none}' +
    '#sr-bubble.on{opacity:1;transform:scale(1)}' +
    '#sr-bubble .sr-lb{display:block;font-size:15px;font-weight:700;letter-spacing:1.2px;' +
    'text-transform:uppercase;color:var(--accent,#2f81f7);margin-bottom:7px}' +
    '#sr-bubble i.sr-ar{position:absolute;width:16px;height:16px;background:#0b1220;' +
    'border-left:3px solid var(--accent,#2f81f7);border-top:3px solid var(--accent,#2f81f7);' +
    'transform:rotate(45deg)}' +
    '#sr-toggle{display:inline-flex;align-items:center;gap:6px;cursor:pointer;' +
    'background:var(--surface-2,#1b2330);border:1px solid var(--border,#2d3748);color:var(--text,#e6edf3);' +
    'border-radius:7px;padding:5px 10px;font-size:13px;font-weight:600}' +
    '#sr-toggle.off{opacity:.5}' +
    '@media print{#sr-bubble{display:none!important}}';
  document.head.appendChild(css);

  var bub = document.createElement('div');
  bub.id = 'sr-bubble';
  bub.innerHTML = '<i class="sr-ar"></i><span class="sr-lb"></span><span class="sr-tx"></span>';
  document.body.appendChild(bub);
  var arrow = bub.querySelector('.sr-ar');
  var lbEl = bub.querySelector('.sr-lb');
  var txEl = bub.querySelector('.sr-tx');

  // ── Yardımcılar ────────────────────────────────────────────────────────
  var SKIP = { SCRIPT: 1, STYLE: 1, SVG: 1, PATH: 1, CANVAS: 1, HTML: 1, BODY: 1 };

  function labelFor(el) {
    var t = el.tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return 'Alan';
    if (t === 'BUTTON' || (t === 'A' && el.className.indexOf('btn') >= 0)) return 'Buton';
    if (t === 'A') return 'Bağlantı';
    if (t === 'TH') return 'Sütun';
    if (t === 'LABEL') return 'Etiket';
    if (/^H[1-6]$/.test(t)) return 'Başlık';
    return '';
  }

  function textOf(el) {
    var t = el.tagName;
    if (t === 'INPUT') {
      if (el.type === 'checkbox' || el.type === 'radio')
        return el.checked ? 'İşaretli' : 'İşaretli değil';
      return el.value || el.placeholder || '';
    }
    if (t === 'TEXTAREA') return el.value || el.placeholder || '';
    if (t === 'SELECT') {
      var o = el.options[el.selectedIndex];
      return o ? o.text : '';
    }
    if (t === 'IMG') return el.alt || '';
    return (el.innerText || el.textContent || '');
  }

  /* İmlecin tam altındaki metin parçasının sahibi olan en küçük öğeyi bulur. */
  function targetAt(x, y) {
    var el = document.elementFromPoint(x, y);
    if (!el || el.id === 'sr-bubble' || bub.contains(el)) return null;

    var tag = el.tagName;
    if (SKIP[tag]) return null;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'IMG') return el;

    // Metin düğümünü hassas biçimde yakala
    var node = null;
    if (document.caretRangeFromPoint) {
      var r = document.caretRangeFromPoint(x, y);
      if (r) node = r.startContainer;
    } else if (document.caretPositionFromPoint) {
      var p = document.caretPositionFromPoint(x, y);
      if (p) node = p.offsetNode;
    }
    if (node && node.nodeType === 3 && node.parentElement) {
      var pe = node.parentElement;
      if (!SKIP[pe.tagName] && !bub.contains(pe)) return pe;
    }

    // Geri dönüş: kendi doğrudan metni olan en yakın ata
    var cur = el, hops = 0;
    while (cur && hops++ < 3) {
      if (SKIP[cur.tagName]) break;
      var own = '';
      for (var i = 0; i < cur.childNodes.length; i++)
        if (cur.childNodes[i].nodeType === 3) own += cur.childNodes[i].nodeValue;
      if (own.trim()) return cur;
      cur = cur.parentElement;
    }
    return null;
  }

  function place(rect, mx, my) {
    bub.style.display = 'block';
    bub.style.left = '-9999px';
    bub.style.top = '0px';
    var bw = bub.offsetWidth, bh = bub.offsetHeight;
    var vw = window.innerWidth, vh = window.innerHeight, gap = 16;

    // Varsayılan: hedefin üstünde, yatayda ortalı
    var left = (rect.left + rect.width / 2) - bw / 2;
    var top = rect.top - bh - gap;
    var below = false;
    if (top < 8) { top = rect.bottom + gap; below = true; }
    if (top + bh > vh - 8) top = Math.max(8, vh - bh - 8);
    left = Math.min(Math.max(8, left), vw - bw - 8);

    bub.style.left = Math.round(left) + 'px';
    bub.style.top = Math.round(top) + 'px';

    // Oku hedefe doğrult
    var ax = Math.min(Math.max(rect.left + rect.width / 2 - left, 18), bw - 30);
    arrow.style.left = Math.round(ax) + 'px';
    if (below) {
      arrow.style.top = '-9px';
      arrow.style.transform = 'rotate(45deg)';
    } else {
      arrow.style.top = (bh - 9) + 'px';
      arrow.style.transform = 'rotate(225deg)';
    }
  }

  var timer = null, lastEl = null;

  function hide() {
    bub.classList.remove('on');
    bub.style.display = 'none';
    lastEl = null;
  }

  function show(el, mx, my) {
    var txt = (textOf(el) || '').replace(/\s+\n/g, '\n').trim();
    if (!txt) { hide(); return; }
    if (txt.length > MAX_CHARS) txt = txt.slice(0, MAX_CHARS) + '…';

    var rect = el.getBoundingClientRect();
    if (!rect.width || !rect.height) { hide(); return; }
    // Zaten çok büyük yazıları büyütmenin anlamı yok
    var fs = parseFloat(getComputedStyle(el).fontSize) || 14;
    if (fs >= 28 && txt.length < 40) { hide(); return; }

    var lb = labelFor(el);
    lbEl.textContent = lb;
    lbEl.style.display = lb ? 'block' : 'none';
    txEl.textContent = txt;
    place(rect, mx, my);
    bub.classList.add('on');
    lastEl = el;
  }

  document.addEventListener('mousemove', function (e) {
    if (paused) return;
    clearTimeout(timer);
    var x = e.clientX, y = e.clientY;
    timer = setTimeout(function () {
      var el = targetAt(x, y);
      if (!el) { hide(); return; }
      if (el === lastEl) return;
      show(el, x, y);
    }, DELAY);
  }, true);

  document.addEventListener('mouseleave', hide, true);
  document.addEventListener('scroll', hide, true);
  window.addEventListener('blur', hide);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') hide();
  });

  // ── Üst bardaki aç/kapat düğmesi ───────────────────────────────────────
  function paint(btn) {
    btn.classList.toggle('off', paused);
    btn.title = paused ? 'Dede modu kapalı — açmak için tıklayın'
                       : 'Dede modu açık — kapatmak için tıklayın';
    btn.querySelector('.sr-st').textContent = paused ? 'Kapalı' : 'Açık';
  }

  window.__seniorMountToggle = function (host) {
    if (!host || document.getElementById('sr-toggle')) return;
    var b = document.createElement('button');
    b.id = 'sr-toggle';
    b.type = 'button';
    b.innerHTML = '<span style="font-size:15px;">🔍</span><span>Büyüteç: <span class="sr-st"></span></span>';
    b.onclick = function () {
      paused = !paused;
      try { localStorage.setItem(OFF_KEY, paused ? '1' : '0'); } catch (e) {}
      if (paused) hide();
      paint(b);
    };
    host.appendChild(b);
    paint(b);
  };
})();
