/* Parametrik kesim — fareyle döndürülebilir 3B önizleme.
   Harici kütüphane yok: düz canvas 2B, ortografik izdüşüm, ressam algoritması.

   Geometri: her parça bir ekstrüzyon (kapalı kontur + kalınlık).
     o=0 → panel : kontur (y,z), x ekseni boyunca ekstrüde
     o=1 → kayıt : kontur (x,z), y ekseni boyunca ekstrüde            */

(function (global) {
  'use strict';

  function P3D(canvas, opts) {
    this.cv = canvas;
    this.ctx = canvas.getContext('2d');
    this.opts = opts || {};
    this.yaw = -0.60;
    this.pitch = 0.32;
    this.zoom = 0.86;
    this.panX = 0;
    this.panY = 0;
    this.faces = [];
    this.center = [0, 0, 0];
    this.radius = 1;
    this.ready = false;
    this._bind();
  }

  P3D.prototype.load = function (data) {
    var bb = data.bb || [0, 0, 0, 1, 1, 1];
    this.center = [(bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2];
    this.radius = Math.max(bb[3] - bb[0], bb[4] - bb[1], bb[5] - bb[2], 1) / 2;

    var faces = [];
    var parts = data.parts || [];

    for (var i = 0; i < parts.length; i++) {
      var pt = parts[i];
      var isFrame = pt.o === 1;
      var a = pt.p, b = pt.p + pt.t;

      for (var li = 0; li < pt.l.length; li++) {
        var lp = pt.l[li];
        var n = lp.length;
        var front = new Array(n), back = new Array(n);

        for (var k = 0; k < n; k++) {
          var u = lp[k][0], v = lp[k][1];
          // düzlem koordinatlarını dünya koordinatına taşı
          front[k] = isFrame ? [u, a, v] : [a, u, v];
          back[k] = isFrame ? [u, b, v] : [b, u, v];
        }
        // yan yüzeyler
        for (var k2 = 0; k2 < n; k2++) {
          var j = (k2 + 1) % n;
          faces.push({ v: [front[k2], front[j], back[j], back[k2]], f: isFrame });
        }
        // kapaklar
        faces.push({ v: front, f: isFrame, cap: 1 });
        faces.push({ v: back.slice().reverse(), f: isFrame, cap: 1 });
      }
    }
    this.faces = faces;
    this.ready = true;
    this.draw();
  };

  P3D.prototype._rot = function (p) {
    var x = p[0] - this.center[0];
    var y = p[1] - this.center[1];
    var z = p[2] - this.center[2];
    var ca = Math.cos(this.yaw), sa = Math.sin(this.yaw);
    var rx = x * ca - y * sa;
    var ry = x * sa + y * ca;
    var cb = Math.cos(this.pitch), sb = Math.sin(this.pitch);
    var ry2 = ry * cb - z * sb;
    var rz2 = ry * sb + z * cb;
    return [rx, ry2, rz2];   // [ekran-x, derinlik, ekran-yukarı]
  };

  P3D.prototype.draw = function () {
    if (!this.ready) return;
    var dpr = global.devicePixelRatio || 1;
    var W = this.cv.clientWidth, H = this.cv.clientHeight;
    if (this.cv.width !== W * dpr || this.cv.height !== H * dpr) {
      this.cv.width = W * dpr;
      this.cv.height = H * dpr;
    }
    var g = this.ctx;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, W, H);

    var s = Math.min(W, H) / (this.radius * 2.35) * this.zoom;
    var cx = W / 2 + this.panX, cy = H / 2 + this.panY;

    var list = [];
    for (var i = 0; i < this.faces.length; i++) {
      var fc = this.faces[i];
      var vs = fc.v, n = vs.length;
      var px = new Array(n), py = new Array(n);
      var dsum = 0, area = 0;
      var r0 = null, r1 = null, r2 = null;

      for (var k = 0; k < n; k++) {
        var r = this._rot(vs[k]);
        px[k] = cx + r[0] * s;
        py[k] = cy - r[2] * s;
        dsum += r[1];
        if (k === 0) r0 = r; else if (k === 1) r1 = r; else if (k === 2) r2 = r;
      }
      for (var k3 = 0; k3 < n; k3++) {
        var j = (k3 + 1) % n;
        area += px[k3] * py[j] - px[j] * py[k3];
      }
      if (area >= 0) continue;                  // arkaya bakan yüz — atla

      // 3B normal (aydınlatma için)
      var ux = r1[0] - r0[0], uy = r1[1] - r0[1], uz = r1[2] - r0[2];
      var wx = r2[0] - r0[0], wy = r2[1] - r0[1], wz = r2[2] - r0[2];
      var nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
      var nl = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
      nx /= nl; ny /= nl; nz /= nl;
      if (ny > 0) { nx = -nx; ny = -ny; nz = -nz; }   // yüzey kameraya baksın
      // ışık yönü (ekran uzayı): soldan, önden, yukarıdan
      var lam = nx * -0.34 + ny * -0.86 + nz * 0.38;
      if (lam < 0) lam = 0;
      var sh = 0.46 + 0.52 * lam + 0.12 * (nz > 0 ? nz : 0);

      list.push({ px: px, py: py, d: dsum / n, sh: sh, f: fc.f });
    }

    list.sort(function (a, b) { return b.d - a.d; });   // uzaktan yakına

    // derinlik ipucu: uzak parçalar koyulaşsın (paralel panellerde form okunsun)
    var dmin = Infinity, dmax = -Infinity;
    for (var n0 = 0; n0 < list.length; n0++) {
      if (list[n0].d < dmin) dmin = list[n0].d;
      if (list[n0].d > dmax) dmax = list[n0].d;
    }
    var dspan = (dmax - dmin) || 1;

    for (var m = 0; m < list.length; m++) {
      var it = list[m];
      var fog = 1 - 0.26 * ((it.d - dmin) / dspan);
      var base = it.f ? [150, 112, 64] : [208, 170, 112];
      var k = it.sh * fog;
      var R = Math.min(255, Math.round(base[0] * k)),
          G = Math.min(255, Math.round(base[1] * k)),
          B = Math.min(255, Math.round(base[2] * k));
      g.beginPath();
      g.moveTo(it.px[0], it.py[0]);
      for (var q = 1; q < it.px.length; q++) g.lineTo(it.px[q], it.py[q]);
      g.closePath();
      g.fillStyle = 'rgb(' + R + ',' + G + ',' + B + ')';
      g.fill();
      g.strokeStyle = 'rgba(0,0,0,0.20)';
      g.lineWidth = 0.5;
      g.stroke();
    }
  };

  P3D.prototype.view = function (yaw, pitch) {
    this.yaw = yaw; this.pitch = pitch;
    this.panX = this.panY = 0;
    this.draw();
  };

  P3D.prototype._bind = function () {
    var self = this, drag = null;

    function down(e) {
      var t = e.touches ? e.touches[0] : e;
      drag = { x: t.clientX, y: t.clientY, shift: e.shiftKey || (e.touches && e.touches.length > 1) };
      self.cv.style.cursor = 'grabbing';
      if (e.cancelable) e.preventDefault();
    }
    function move(e) {
      if (!drag) return;
      var t = e.touches ? e.touches[0] : e;
      var dx = t.clientX - drag.x, dy = t.clientY - drag.y;
      drag.x = t.clientX; drag.y = t.clientY;
      if (drag.shift) {
        self.panX += dx; self.panY += dy;
      } else {
        self.yaw += dx * 0.011;
        self.pitch += dy * 0.011;
        var lim = Math.PI / 2 * 1.35;
        if (self.pitch > lim) self.pitch = lim;
        if (self.pitch < -lim) self.pitch = -lim;
      }
      self.draw();
      if (e.cancelable) e.preventDefault();
    }
    function up() { drag = null; self.cv.style.cursor = 'grab'; }

    this.cv.addEventListener('mousedown', down);
    global.addEventListener('mousemove', move);
    global.addEventListener('mouseup', up);
    this.cv.addEventListener('touchstart', down, { passive: false });
    this.cv.addEventListener('touchmove', move, { passive: false });
    this.cv.addEventListener('touchend', up);

    this.cv.addEventListener('wheel', function (e) {
      self.zoom *= e.deltaY < 0 ? 1.12 : 1 / 1.12;
      if (self.zoom < 0.15) self.zoom = 0.15;
      if (self.zoom > 12) self.zoom = 12;
      self.draw();
      e.preventDefault();
    }, { passive: false });

    this.cv.addEventListener('dblclick', function () {
      self.zoom = 0.86; self.view(-0.60, 0.32);
    });
    this.cv.style.cursor = 'grab';
    global.addEventListener('resize', function () { self.draw(); });
  };

  global.Parametric3D = {
    mount: function (canvasId, url, statusId) {
      var cv = document.getElementById(canvasId);
      if (!cv) return null;
      var v = new P3D(cv);
      var st = statusId ? document.getElementById(statusId) : null;
      fetch(url, { credentials: 'same-origin' })
        .then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function (d) {
          v.load(d);
          if (st) st.textContent = (d.np || 0) + ' panel' +
            (d.nf ? ' + ' + d.nf + ' kayıt' : '') + ' · sürükle: döndür · tekerlek: yakınlaş';
        })
        .catch(function (err) {
          if (st) st.textContent = '3B önizleme yüklenemedi (' + err.message + ')';
        });
      return v;
    }
  };
})(window);
