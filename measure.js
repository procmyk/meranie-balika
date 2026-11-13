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
  // RANSAC: zvislé roviny (normála vodorovná) medzi vyvýšenými bodmi; ak je to stena, body vyradíme.
  function removeWalls(pts, elevated, cols, rows, floorY, opts) {
    const idx = [];
    for (let i = 0; i < elevated.length; i++) if (elevated[i]) idx.push(i);
    for (let wall = 0; wall < 2 && idx.length > 80; wall++) {
      let best = null, bestCnt = 0;
      let seedR = 12345 + wall;
      const rnd = () => (seedR = (seedR * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
      for (let it = 0; it < 120; it++) {
        const a = idx[(rnd() * idx.length) | 0], b = idx[(rnd() * idx.length) | 0];
        const dx = pts[b*3] - pts[a*3], dz = pts[b*3+2] - pts[a*3+2], l = Math.hypot(dx, dz);
        if (l < 0.2) continue;
        const nx = -dz / l, nz = dx / l, d0 = nx * pts[a*3] + nz * pts[a*3+2];
        let cnt = 0;
        for (let k = 0; k < idx.length; k += 3) { const i = idx[k]; if (Math.abs(nx * pts[i*3] + nz * pts[i*3+2] - d0) < opts.wallTol) cnt++; }
        if (cnt > bestCnt) { bestCnt = cnt; best = [nx, nz, d0]; }
      }
      if (!best) return;
      const [nx, nz, d0] = best;
      const inl = idx.filter(i => Math.abs(nx * pts[i*3] + nz * pts[i*3+2] - d0) < opts.wallTol);
      if (inl.length < 60) return;
      let maxH = 0, touchTop = 0, minT = Infinity, maxT = -Infinity;
      for (const i of inl) {
        maxH = Math.max(maxH, pts[i*3+1] - floorY);
        if (i < cols * 2) touchTop++;                       // horné 2 riadky obrazu
        const t = -nz * pts[i*3] + nx * pts[i*3+2];
        if (t < minT) minT = t; if (t > maxT) maxT = t;
      }
      const isWall = (maxH > opts.wallMinH || touchTop >= 3) && maxT - minT > 0.5;
      if (!isWall) return;
      for (const i of inl) elevated[i] = 0;
      const rest = idx.filter(i => elevated[i]);
      idx.length = 0; idx.push(...rest);
    }
  }

  function detectBox(grid, floorY, opts) {
    opts = Object.assign({ minH: 0.02, maxH: 2.0, link: 0.05, minPts: 40, topBand: 0.03, wallTol: 0.03, wallMinH: 0.85 }, opts || {});
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
    // Steny: veľká zvislá plocha, ktorá siaha vyššie ako bežný balík alebo za horný okraj obrazu,
    // nie je balík. Bez toho sa stena za balíkom „prilepí“ (telefón vyhladzuje hĺbku na hranách).
    removeWalls(pts, elevated, cols, rows, floorY, opts);

    // Začiatok (seed): vyvýšené body podľa vzdialenosti od stredu obrazu. Skúšame postupne,
    // kým z niektorého nevyrastie dosť veľký objekt (osamelý šumový bod alebo podlaha v otvore
    // pneumatiky by inak meranie zablokovali).
    const cc = (cols - 1) / 2, cr = (rows - 1) / 2;
    const maxR = Math.min(cols, rows) * 0.35;
    const cand = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      if (!elevated[i]) continue;
      const d = (c - cc) * (c - cc) + (r - cr) * (r - cr);
      if (d < maxR * maxR) cand.push([d, i]);
    }
    if (!cand.length) return null;
    cand.sort((a, b) => a[0] - b[0]);

    // rast oblasti po mriežke
    const inComp = new Uint8Array(n);
    const link2 = opts.link * opts.link;
    const grow = seed => {
      const queue = [seed], out = [];
      inComp[seed] = 1;
      while (queue.length) {
        const i = queue.pop();
        out.push(i);
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
      return out;
    };
    let comp = [];
    for (let k = 0, tries = 0; k < cand.length && tries < 40; k++) {
      const i = cand[k][1];
      if (inComp[i]) continue;
      tries++;
      comp = grow(i);
      if (comp.length >= opts.minPts) break;
    }
    if (comp.length < opts.minPts) return null;
    // dotýka sa balík okraja obrazu? -> nie je celý v zábere, rozmery by boli skreslené
    let cut = false;
    for (const i of comp) {
      const r = (i / cols) | 0, c = i - r * cols;
      if (r === 0 || c === 0 || r === rows - 1 || c === cols - 1) { cut = true; break; }
    }

    const hs = comp.map(i => pts[i*3+1] - floorY).sort((a, b) => a - b);
    const hTop = percentile(hs, 0.95);
    const top = comp.filter(i => pts[i*3+1] - floorY > hTop - opts.topBand);
    if (top.length < opts.minPts / 2) return null;
    const height = median(top.map(i => pts[i*3+1] - floorY));
    // Pôdorys z hornej polovice balíka: pri krabici = vrchná stena + horné časti bokov,
    // pri valci / vreci zachytí najširšie miesto (samotný vrch je pri valci len úzky pásik).
    // Spodnú polovicu vynechávame – na hranách tam býva šum (hĺbka „preteká“ na podlahu).
    let foot = comp.filter(i => pts[i*3+1] - floorY > 0.5 * height);
    if (foot.length < top.length) foot = top;
    const rect = robustRect(foot.map(i => [pts[i*3], pts[i*3+2]]));
    let L = Math.max(rect.lenU, rect.lenV), W = Math.min(rect.lenU, rect.lenV);
    let corners = rect.corners, shape = 'krabica';

    // Zaoblené tvary: rez balíkom (vodorovná poloha × výška) porovnáme s kružnicou
    // (polomer = výška/2, leží na podlahe) a s obdĺžnikom (vrch + zvislé steny).
    //  - priečny rez kruhový  -> ležiaci valec (stočený matrac): šírka = priemer = výška
    //  - pozdĺžny rez kruhový -> stojace koleso / pneumatika: dĺžka = priemer = výška
    // Zo šikmého pohľadu kamera nevidí zadnú polovicu oblúka, preto rozmer dopočítame.
    const cx = (corners[0][0] + corners[2][0]) / 2, cz = (corners[0][1] + corners[2][1]) / 2;
    const longAng = rect.lenU >= rect.lenV ? rect.angle : rect.angle + Math.PI / 2;
    const R = height / 2;
    const sel = comp.filter(i => pts[i*3+1] - floorY > 0.15 * height);
    const stepS = Math.max(1, Math.floor(sel.length / 400));   // ~400 bodov stačí, výpočet je rýchly
    const sub = [];
    for (let k = 0; k < sel.length; k += stepS) sub.push(sel[k]);
    const circleFit = ang => {
      const ax = Math.cos(ang), az = Math.sin(ang);
      const ls = sub.map(i => (pts[i*3] - cx) * ax + (pts[i*3+2] - cz) * az);
      const hs2 = sub.map(i => pts[i*3+1] - floorY);
      const sl = ls.slice().sort((a, b) => a - b);
      const l0 = percentile(sl, 0.02), l1 = percentile(sl, 0.98);
      const rb = median(ls.map((l, k) => Math.min(Math.abs(hs2[k] - height), Math.abs(l - l0), Math.abs(l - l1))));
      // poloha osi: najprv hrubo (2 cm), potom jemne (5 mm) okolo najlepšej
      const resid = c => median(ls.map((l, k) => Math.abs(Math.hypot(l - c, hs2[k] - R) - R)));
      let rc = Infinity, c0 = 0;
      for (let c = l0 - R; c <= l1 + R; c += 0.02) { const r = resid(c); if (r < rc) { rc = r; c0 = c; } }
      for (let c = c0 - 0.02, cEnd = c0 + 0.02; c <= cEnd; c += 0.005) { const r = resid(c); if (r < rc) { rc = r; c0 = c; } }
      return { round: rc < 0.7 * rb, c: c0, ax, az };
    };
    if (height > 0.06 && sub.length >= 40) {
      let lat = null, lon = null;
      if (L > 1.1 * height && W < 1.2 * height) lat = circleFit(longAng + Math.PI / 2);
      if (!(lat && lat.round) && L < 1.2 * height && height > 0.2) lon = circleFit(longAng);
      if (lat && lat.round) {
        shape = 'valec';
        W = Math.max(W, height);
      } else if (lon && lon.round) {
        shape = 'koleso';
        L = Math.max(L, height);
      }
      if (shape !== 'krabica') {
        // rámik: stred posunutý na os oblúka, rozmery doplnené
        const ux = Math.cos(longAng), uz = Math.sin(longAng), vx = -uz, vz = ux;
        let mx = cx, mz = cz;
        if (lat && lat.round) { mx += lat.ax * lat.c; mz += lat.az * lat.c; }
        else { mx += lon.ax * lon.c; mz += lon.az * lon.c; }
        corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) =>
          [mx + ux * a * L / 2 + vx * b * W / 2, mz + uz * a * L / 2 + vz * b * W / 2]);
        if (W > L) { const t = L; L = W; W = t; }
      }
    }
    // Pneumatika? Typické rozmery (priemer 40–110 cm, šírka 10–45 cm) a:
    //  - ležiaca: okrúhly pôdorys a v strede otvor, cez ktorý kamera vidí podlahu,
    //  - stojaca: rozpoznaná ako koleso (kruhový profil po dĺžke).
    const D = L, T = shape === 'koleso' ? W : height;
    const tireSize = D >= 0.4 && D <= 1.1 && T >= 0.1 && T <= 0.45 && T < 0.6 * D;
    if (tireSize && shape === 'koleso') shape = 'pneumatika';
    else if (tireSize && shape === 'krabica' && W > 0.85 * L) {
      const mx = (corners[0][0] + corners[2][0]) / 2, mz = (corners[0][1] + corners[2][1]) / 2;
      const rIn = 0.25 * L;
      let low = 0, high = 0;
      for (let i = 0; i < n; i++) {
        const y = pts[i * 3 + 1];
        if (y !== y) continue;
        const dx = pts[i * 3] - mx, dz = pts[i * 3 + 2] - mz;
        if (dx * dx + dz * dz > rIn * rIn) continue;
        const h = y - floorY;
        if (h < 0.3 * height) low++; else if (h > 0.7 * height) high++;
      }
      if (low >= 3 && low > 2 * high) shape = 'pneumatika';
    }
    return { length: L, width: W, height, corners, shape, cut, floorY, topY: floorY + height, count: comp.length };
  }

  // Zhrnutie viacerych meranii (median kazdeho rozmeru).
  function aggregate(list) {
    if (!list.length) return null;
    return {
      length: median(list.map(m => m.length)),
      width: median(list.map(m => m.width)),
      height: median(list.map(m => m.height)),
      shape: (() => { const c = {}; for (const m of list) c[m.shape || 'krabica'] = (c[m.shape || 'krabica'] || 0) + 1;
        return Object.keys(c).sort((a, b) => c[b] - c[a])[0]; })(),
      samples: list.length,
    };
  }

  // Kategórie balíkov podľa rozmerov (cm). Balík patrí do prvej, do ktorej sa zmestí v ľubovoľnom otočení.
  const CATEGORIES = [
    { id: 'XS', max: [25, 20, 10], color: '#4fc3f7' },
    { id: 'S', max: [40, 30, 15], color: '#3ddc84' },
    { id: 'M', max: [60, 40, 30], color: '#ffcc00' },
    { id: 'L', max: [80, 60, 40], color: '#ff9800' },
    { id: 'XL', max: [120, 80, 60], color: '#f44336' },
  ];
  const OVERSIZE = { id: 'NADROZMER', max: null, color: '#b388ff' };

  function categorize(L, W, H) {
    const d = [L, W, H].sort((a, b) => b - a);
    for (const c of CATEGORIES) if (d[0] <= c.max[0] && d[1] <= c.max[1] && d[2] <= c.max[2]) return c;
    return OVERSIZE;
  }

  const api = { CATEGORIES, OVERSIZE, categorize, mulVec, invert, viewRay, unproject, percentile, median, convexHull, minAreaAngle, robustRect, detectBox, aggregate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Measure = api;
})(this);
