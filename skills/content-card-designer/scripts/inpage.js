/* In-page fitting and quality checks. Runs inside the headless browser.
 * 1. Fit: find the font scale (--s) at which the content fills the card without overflowing.
 * 2. Measure: overflow, minimum font size, fill, contrast, short last lines.
 * Results are written to <pre id="qa"> as JSON for the Python side to read. */
(function () {
  var NOTEXT = /[?&]notext=1/.test(location.search);
  if (NOTEXT) document.documentElement.classList.add('notext');

  function parseColor(c) {
    var m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    var p = m[1].split(',').map(parseFloat);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  }
  function chan(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  function lum(c) { return 0.2126 * chan(c.r) + 0.7152 * chan(c.g) + 0.0722 * chan(c.b); }
  function ratio(a, b) {
    var l1 = lum(a), l2 = lum(b);
    if (l1 < l2) { var t = l1; l1 = l2; l2 = t; }
    return (l1 + 0.05) / (l2 + 0.05);
  }
  function backdrop(el, card) {
    // nearest ancestor (inside the card) with a solid background; otherwise a photo if the card has one
    while (el && el !== card) {
      var cs = getComputedStyle(el);
      var bg = parseColor(cs.backgroundColor);
      if (cs.backgroundImage !== 'none') return { image: true };
      if (bg && bg.a > 0.5) return bg;
      el = el.parentElement;
    }
    if (card.querySelector(':scope > .bgimg')) return { image: true };
    var cb = parseColor(getComputedStyle(card).backgroundColor);
    return cb || { r: 255, g: 255, b: 255, a: 1 };
  }
  function textLeaves(card) {
    var out = [], seen = new Set();
    var w = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = w.nextNode())) {
      if (!n.nodeValue.trim()) continue;
      var el = n.parentElement;
      if (!el || /^(SCRIPT|STYLE|PRE)$/.test(el.tagName) || el.closest('pre')) continue;
      out.push({ node: n, el: el });
    }
    return out;
  }
  function lastLine(node) {
    var r = document.createRange();
    r.selectNodeContents(node);
    var rects = Array.from(r.getClientRects()).filter(function (x) { return x.width > 0 && x.height > 0; });
    if (!rects.length) return null;
    var tops = [];
    rects.forEach(function (x) {
      var t = Math.round(x.top / 4) * 4;
      if (tops.indexOf(t) === -1) tops.push(t);
    });
    var last = rects.filter(function (x) { return Math.round(x.top / 4) * 4 === tops[tops.length - 1]; });
    var width = last.reduce(function (s, x) { return s + x.width; }, 0);
    return { lines: tops.length, width: width };
  }

  function fitCard(card) {
    var main = card.querySelector('.main'), inner = card.querySelector('.inner');
    var u = parseFloat(getComputedStyle(card).getPropertyValue('--u')) || 1;
    var minFont = parseFloat(card.dataset.minfont) || 34;
    var baseMin = parseFloat(card.dataset.basemin) || 34;
    var mode = card.dataset.fit || 'fill';
    var maxS = parseFloat(card.dataset.maxscale) || (mode === 'fill' ? 1.3 : 1.0);
    var lo = 0.5; // small text is clamped to the minimum font in CSS, so the card can shrink below 1
    card.classList.add('measure');
    var H = main.clientHeight, W = main.clientWidth;
    function fits(s) {
      card.style.setProperty('--s', s);
      return inner.getBoundingClientRect().height <= H * 0.965 && inner.scrollWidth <= W + 1;
    }
    var best = lo, status = 'ok';
    if (!fits(lo)) {
      status = 'overflow';
    } else {
      var a = lo, b = Math.max(lo, maxS);
      if (fits(b)) { best = b; }
      else {
        for (var i = 0; i < 14; i++) {
          var m = (a + b) / 2;
          if (fits(m)) a = m; else b = m;
        }
        best = a;
      }
    }
    card.style.setProperty('--s', best);
    var natural = inner.getBoundingClientRect().height;
    var natW = inner.scrollWidth;
    card.classList.remove('measure');
    return { scale: +best.toFixed(3), status: status, H: H, natural: natural, naturalW: natW, W: W, minFontAllowed: minFont };
  }

  function measureCard(card, fit) {
    var cr = card.getBoundingClientRect();
    var leaves = textLeaves(card);
    var minFont = 999, contrastIssues = [], shortLast = [], photoText = [];
    leaves.forEach(function (t) {
      var cs = getComputedStyle(t.el);
      var fs = parseFloat(cs.fontSize);
      if (fs < minFont) minFont = fs;
      var fg = parseColor(cs.color);
      var bd = backdrop(t.el, card);
      var snippet = t.node.nodeValue.trim().slice(0, 18);
      var r = t.el.getBoundingClientRect();
      if (bd.image) {
        photoText.push({ x: r.left - cr.left, y: r.top - cr.top, w: r.width, h: r.height, fs: fs,
          color: fg ? [fg.r, fg.g, fg.b] : [0, 0, 0], text: snippet });
      } else if (fg && !NOTEXT) {
        var need = (fs >= 32 || (fs >= 24 && parseInt(cs.fontWeight, 10) >= 700)) ? 3.0 : 4.5;
        var rt = ratio(fg, bd);
        if (rt < need) contrastIssues.push({ text: snippet, ratio: +rt.toFixed(2), need: need });
      }
      var ll = lastLine(t.node);
      if (ll && ll.lines >= 2 && ll.width < fs * 2.3 && t.node.nodeValue.trim().length > 6) {
        shortLast.push({ text: snippet, lastLineWidth: Math.round(ll.width), fontSize: Math.round(fs) });
      }
    });
    var main = card.querySelector('.main');
    var fill = fit.H ? fit.natural / fit.H : 0;
    var overflow = fit.status === 'overflow' || fit.naturalW > fit.W + 1;
    var clipped = false;
    card.querySelectorAll('.inner *').forEach(function (e) {
      var r = e.getBoundingClientRect();
      if (r.width && r.height && (r.right > cr.right + 1 || r.bottom > cr.bottom + 1 || r.left < cr.left - 1 || r.top < cr.top - 1)) clipped = true;
    });
    return {
      layout: card.dataset.layout, scale: fit.scale, fitStatus: fit.status,
      overflow: overflow || clipped, minFont: Math.round(minFont * 10) / 10, minFontRequired: fit.minFontAllowed,
      fillPct: Math.round(fill * 100), contrastIssues: contrastIssues, shortLastLines: shortLast,
      photoText: photoText, w: Math.round(cr.width), h: Math.round(cr.height)
    };
  }

  function run() {
    var cards = Array.from(document.querySelectorAll('.card'));
    var res = cards.map(function (c) {
      var f = fitCard(c);
      return measureCard(c, f);
    });
    var pre = document.getElementById('qa');
    if (!pre) { pre = document.createElement('pre'); pre.id = 'qa'; pre.style.display = 'none'; document.body.appendChild(pre); }
    pre.textContent = JSON.stringify(res);
    try { console.log('QA_B64:' + btoa(unescape(encodeURIComponent(JSON.stringify(res))))); } catch (e) {}
    document.documentElement.setAttribute('data-ready', '1');
  }
  run();                                   // first pass as soon as the DOM exists, so a screenshot taken early is already fitted
  window.addEventListener('load', run);    // second pass once everything has loaded (idempotent)
})();
