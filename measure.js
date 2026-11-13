// Geometria merania balika – nezavisla od WebXR, testovatelna v Node.
(function (root) {
  'use strict';

  // --- 4x4 matice (column-major, ako WebXR) ---
  function mulVec(m, x, y, z, w) {
    return [
      m[0] * x + m[4] * y + m[8] * z + m[12] * w,
      m[1] * x + m[5] * y + m[9] * z + m[13] * w,
      m[2] * x + m[6] * y + m[10] * z + m[14] * w,
      m[3] * x + m[7] * y + m[11] * z + m[15] * w,
    ];
  }

  function invert(m) {
    const inv = new Float32Array(16);
    inv[0] = m[5]*m[10]*m[15]-m[5]*m[11]*m[14]-m[9]*m[6]*m[15]+m[9]*m[7]*m[14]+m[13]*m[6]*m[11]-m[13]*m[7]*m[10];
    inv[4] = -m[4]*m[10]*m[15]+m[4]*m[11]*m[14]+m[8]*m[6]*m[15]-m[8]*m[7]*m[14]-m[12]*m[6]*m[11]+m[12]*m[7]*m[10];
    inv[8] = m[4]*m[9]*m[15]-m[4]*m[11]*m[13]-m[8]*m[5]*m[15]+m[8]*m[7]*m[13]+m[12]*m[5]*m[11]-m[12]*m[7]*m[9];
    inv[12] = -m[4]*m[9]*m[14]+m[4]*m[10]*m[13]+m[8]*m[5]*m[14]-m[8]*m[6]*m[13]-m[12]*m[5]*m[10]+m[12]*m[6]*m[9];
    inv[1] = -m[1]*m[10]*m[15]+m[1]*m[11]*m[14]+m[9]*m[2]*m[15]-m[9]*m[3]*m[14]-m[13]*m[2]*m[11]+m[13]*m[3]*m[10];
    inv[5] = m[0]*m[10]*m[15]-m[0]*m[11]*m[14]-m[8]*m[2]*m[15]+m[8]*m[3]*m[14]+m[12]*m[2]*m[11]-m[12]*m[3]*m[10];
    inv[9] = -m[0]*m[9]*m[15]+m[0]*m[11]*m[13]+m[8]*m[1]*m[15]-m[8]*m[3]*m[13]-m[12]*m[1]*m[11]+m[12]*m[3]*m[9];
    inv[13] = m[0]*m[9]*m[14]-m[0]*m[10]*m[13]-m[8]*m[1]*m[14]+m[8]*m[2]*m[13]+m[12]*m[1]*m[10]-m[12]*m[2]*m[9];
    inv[2] = m[1]*m[6]*m[15]-m[1]*m[7]*m[14]-m[5]*m[2]*m[15]+m[5]*m[3]*m[14]+m[13]*m[2]*m[7]-m[13]*m[3]*m[6];
    inv[6] = -m[0]*m[6]*m[15]+m[0]*m[7]*m[14]+m[4]*m[2]*m[15]-m[4]*m[3]*m[14]-m[12]*m[2]*m[7]+m[12]*m[3]*m[6];
    inv[10] = m[0]*m[5]*m[15]-m[0]*m[7]*m[13]-m[4]*m[1]*m[15]+m[4]*m[3]*m[13]+m[12]*m[1]*m[7]-m[12]*m[3]*m[5];
    inv[14] = -m[0]*m[5]*m[14]+m[0]*m[6]*m[13]+m[4]*m[1]*m[14]-m[4]*m[2]*m[13]-m[12]*m[1]*m[6]+m[12]*m[2]*m[5];
    inv[3] = -m[1]*m[6]*m[11]+m[1]*m[7]*m[10]+m[5]*m[2]*m[11]-m[5]*m[3]*m[10]-m[9]*m[2]*m[7]+m[9]*m[3]*m[6];
    inv[7] = m[0]*m[6]*m[11]-m[0]*m[7]*m[10]-m[4]*m[2]*m[11]+m[4]*m[3]*m[10]+m[8]*m[2]*m[7]-m[8]*m[3]*m[6];
    inv[11] = -m[0]*m[5]*m[11]+m[0]*m[7]*m[9]+m[4]*m[1]*m[11]-m[4]*m[3]*m[9]-m[8]*m[1]*m[7]+m[8]*m[3]*m[5];
    inv[15] = m[0]*m[5]*m[10]-m[0]*m[6]*m[9]-m[4]*m[1]*m[10]+m[4]*m[2]*m[9]+m[8]*m[1]*m[6]-m[8]*m[2]*m[5];
    let det = m[0]*inv[0]+m[1]*inv[4]+m[2]*inv[8]+m[3]*inv[12];
    if (Math.abs(det) < 1e-12) return null;
    det = 1 / det;
    for (let i = 0; i < 16; i++) inv[i] *= det;
    return inv;
  }

  // Lucovy smer v suradniciach kamery pre normalizovany bod obrazovky (0..1, y dole).
  function viewRay(invProj, u, v) {
    const p = mulVec(invProj, 2 * u - 1, 1 - 2 * v, 1, 1);
    return [p[0] / p[3], p[1] / p[3], p[2] / p[3]];
  }

  // Bod vo svete z hlbky (hlbka = vzdialenost pozdlz -Z kamery).
  function unproject(invProj, viewMatrix, u, v, depth) {
    const d = viewRay(invProj, u, v);
    const s = depth / -d[2];
    const w = mulVec(viewMatrix, d[0] * s, d[1] * s, d[2] * s, 1);
    return [w[0], w[1], w[2]];
  }

  function percentile(sorted, p) {
    if (!sorted.length) return NaN;
    const idx = Math.min(sorted.length - 1, Math.max(0, (sorted.length - 1) * p));
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  }

  function median(arr) {
    return percentile(arr.slice().sort((a, b) => a - b), 0.5);
  }

  // Konvexny obal 2D bodov (monotone chain). pts: [[x,z],...]
  function convexHull(pts) {
    const p = pts.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    if (p.length < 3) return p;
    const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lower = [], upper = [];
    for (const q of p) {
      while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop();
      lower.push(q);
    }
    for (let i = p.length - 1; i >= 0; i--) {
      const q = p[i];
      while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop();
      upper.push(q);
    }
    lower.pop(); upper.pop();
    return lower.concat(upper);
  }

  // Natocenie obdlznika s minimalnou plochou (rotating calipers cez hrany obalu).
  function minAreaAngle(pts) {
    const hull = convexHull(pts);
    if (hull.length < 3) return 0;
    let best = Infinity, bestAng = 0;
    for (let i = 0; i < hull.length; i++) {
      const a = hull[i], b = hull[(i + 1) % hull.length];
      const ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const c = Math.cos(ang), s = Math.sin(ang);
      let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
      for (const q of hull) {
        const u = q[0] * c + q[1] * s, v = -q[0] * s + q[1] * c;
        if (u < minU) minU = u; if (u > maxU) maxU = u;
        if (v < minV) minV = v; if (v > maxV) maxV = v;
      }
      const area = (maxU - minU) * (maxV - minV);
      if (area < best) { best = area; bestAng = ang; }
    }
    return bestAng;
  }

  // Robustny obdlznik: natocenie z obalu, rozmery z percentilov (odolne voci sumu na okrajoch).
  function robustRect(pts, trim) {
    trim = trim == null ? 0.02 : trim;
    const ang = minAreaAngle(pts);
    const c = Math.cos(ang), s = Math.sin(ang);
    const us = [], vs = [];
    for (const q of pts) { us.push(q[0] * c + q[1] * s); vs.push(-q[0] * s + q[1] * c); }
    us.sort((a, b) => a - b); vs.sort((a, b) => a - b);
    const corr = 1 / (1 - 2 * trim); // korekcia na orezanie pri rovnomernom rozlozeni
    const u0 = percentile(us, trim), u1 = percentile(us, 1 - trim);
    const v0 = percentile(vs, trim), v1 = percentile(vs, 1 - trim);
    const uc = (u0 + u1) / 2, vc = (v0 + v1) / 2;
    const lu = (u1 - u0) * corr, lv = (v1 - v0) * corr;
    // rohy spat do (x,z)
    const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => {
      const u = uc + a * lu / 2, v = vc + b * lv / 2;
      return [u * c - v * s, u * s + v * c];
    });
    return { angle: ang, lenU: lu, lenV: lv, corners };
  }

  /**
   * Najde krabicu v mriezke bodov.
   * grid: { cols, rows, pts: Float32Array(cols*rows*3) svetove body (NaN = neplatny) }
   * floorY: vyska podlahy (svet, os Y hore)
   * Vrati null alebo { length, width, height, corners:[[x,z]x4], floorY, topY, count }
   */
  function detectBox(grid, floorY, opts) {
    opts = Object.assign({ minH: 0.02, maxH: 2.0, link: 0.05, minPts: 40, topBand: 0.03 }, opts || {});
    const { cols, rows, pts } = grid;
    const n = cols * rows;
    const elevated = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      const y = pts[i * 3 + 1];
      if (y === y) {
        const h = y - floorY;
        if (h > opts.minH && h < opts.maxH) elevated[i] = 1;
      }
    }
    // seed = vyvyseny bod najblizsie stredu obrazu
    const cc = (cols - 1) / 2, cr = (rows - 1) / 2;
    let seed = -1, bestD = Infinity;
    const maxR = Math.min(cols, rows) * 0.35;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      if (!elevated[i]) continue;
      const d = (c - cc) * (c - cc) + (r - cr) * (r - cr);
      if (d < bestD && d < maxR * maxR) { bestD = d; seed = i; }
    }
    if (seed < 0) return null;

    // rast oblasti po mriezke
    const inComp = new Uint8Array(n);
    const queue = [seed];
    inComp[seed] = 1;
    const comp = [];
    const link2 = opts.link * opts.link;
    while (queue.length) {
      const i = queue.pop();
      comp.push(i);
      const r = (i / cols) | 0, c = i - r * cols;
      const nb = [];
      if (c > 0) nb.push(i - 1);
      if (c < cols - 1) nb.push(i + 1);
      if (r > 0) nb.push(i - cols);
      if (r < rows - 1) nb.push(i + cols);
      for (const j of nb) {
        if (inComp[j] || !elevated[j]) continue;
        const dx = pts[i*3] - pts[j*3], dy = pts[i*3+1] - pts[j*3+1], dz = pts[i*3+2] - pts[j*3+2];
        if (dx*dx + dy*dy + dz*dz < link2) { inComp[j] = 1; queue.push(j); }
      }
    }
    if (comp.length < opts.minPts) return null;

    const hs = comp.map(i => pts[i*3+1] - floorY).sort((a, b) => a - b);
    const hTop = percentile(hs, 0.95);
    const top = comp.filter(i => pts[i*3+1] - floorY > hTop - opts.topBand);
    if (top.length < opts.minPts / 2) return null;
    const height = median(top.map(i => pts[i*3+1] - floorY));
    const rect = robustRect(top.map(i => [pts[i*3], pts[i*3+2]]));
    const L = Math.max(rect.lenU, rect.lenV), W = Math.min(rect.lenU, rect.lenV);
    return { length: L, width: W, height, corners: rect.corners, floorY, topY: floorY + height, count: comp.length };
  }

  // Zhrnutie viacerych meranii (median kazdeho rozmeru).
  function aggregate(list) {
    if (!list.length) return null;
    return {
      length: median(list.map(m => m.length)),
      width: median(list.map(m => m.width)),
      height: median(list.map(m => m.height)),
      samples: list.length,
    };
  }

  const api = { mulVec, invert, viewRay, unproject, percentile, median, convexHull, minAreaAngle, robustRect, detectBox, aggregate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Measure = api;
})(this);
