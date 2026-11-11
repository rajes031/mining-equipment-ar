/* Mining Equipment AR -- viewer logic.
 *
 * The one trick worth knowing: model-viewer's scene graph API can address
 * materials but not nodes, so the GLB generator gives every part its own
 * material named after the part. Fading, highlighting and hiding a single
 * component all go through that material. */

(function () {
  "use strict";

  /* ------------------------------------------------------------ theme */

  try {
    var saved = localStorage.getItem("mining-ar-theme");
    if (saved) document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {}

  document.getElementById("theme").addEventListener("click", function () {
    var root = document.documentElement;
    var dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    var current = root.getAttribute("data-theme") || (dark ? "dark" : "light");
    var next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("mining-ar-theme", next); } catch (e) {}
  });

  /* ------------------------------------------------------------ state */

  var mv = document.getElementById("mv");
  var panel = document.getElementById("panel");
  var id = new URLSearchParams(location.search).get("m") || "dumper";
  var data = null;
  var baseColour = new Map();  // material name -> its as-authored [r,g,b,a]
  var selected = null;
  var tab = "parts";
  var labelsOn = true;
  var figureOn = true;

  var FADED = 0.1;

  /* ------------------------------------------------------- model load */

  fetch("data/" + encodeURIComponent(id) + ".json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(start)
    .catch(function (err) {
      panel.innerHTML =
        '<div class="note"><strong>Could not load this machine</strong>' +
        "Serve the folder over HTTP (<code>python tools/serve.py</code>) " +
        "rather than opening the file directly. (" + err.message + ")</div>";
    });

  function start(d) {
    data = d;
    document.title = d.name + " — Mining Equipment AR";
    document.getElementById("title").textContent = d.name;
    document.getElementById("subtitle").textContent = d.subtitle;
    mv.alt = d.name + ", " + d.subtitle;
    mv.poster = d.thumbnail || "";
    mv.src = d.model;
    buildHotspots();
    render();
  }

  mv.addEventListener("load", function () {
    // Record the as-authored colours by material name, so a faded part can be
    // put back exactly -- including the cab glass, which is translucent to
    // begin with and must return to 0.35 rather than to 1. The material
    // objects themselves are looked up live in setAlpha instead of being
    // stored, which keeps this to one flat map and survives a model swap.
    baseColour.clear();
    (mv.model ? mv.model.materials : []).forEach(function (m) {
      var f = m.pbrMetallicRoughness.baseColorFactor;
      baseColour.set(m.name, [f[0], f[1], f[2], f[3]]);
    });
    applyFigure();
    applySelection();
  });

  /* --------------------------------------------------- part rendering */

  // A part is usually one material, but a part made of more than one
  // substance needs more -- the cab is bodywork AND glass. Those extra
  // materials are named "<part>.<something>", and they must fade with the
  // part, otherwise isolating the tyres leaves the cab windows hanging in
  // mid-air.
  function partOf(materialName) {
    var dot = materialName.indexOf(".");
    return dot === -1 ? materialName : materialName.slice(0, dot);
  }

  function setAlpha(name, alpha) {
    var list = mv.model ? mv.model.materials : [];
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      if (partOf(m.name) !== name) continue;
      var b = baseColour.get(m.name) || m.pbrMetallicRoughness.baseColorFactor;
      var a = alpha === null ? b[3] : alpha;
      try {
        if (m.setAlphaMode) {
          m.setAlphaMode(a < 1 ? "BLEND" : "OPAQUE");
        }
        m.pbrMetallicRoughness.setBaseColorFactor([b[0], b[1], b[2], a]);
      } catch (e) { /* older model-viewer: leave the part as it is */ }
    }
  }

  function applySelection() {
    if (!data) return;
    data.parts.forEach(function (p) {
      if (p.node === "scale_figure") return;
      setAlpha(p.node, selected === null || selected === p.node ? null : FADED);
    });
    applyFigure();
  }

  function applyFigure() {
    setAlpha("scale_figure", figureOn ? (selected && selected !== "scale_figure" ? FADED : null) : 0);
  }

  function buildHotspots() {
    Array.prototype.slice.call(mv.querySelectorAll(".hotspot")).forEach(function (h) {
      h.remove();
    });
    if (!labelsOn) return;
    data.parts.forEach(function (p) {
      if (!p.note) return;
      var b = document.createElement("button");
      b.className = "hotspot";
      b.slot = "hotspot-" + p.node;
      b.dataset.position = p.position.join(" ");
      b.dataset.normal = p.normal.join(" ");
      // model-viewer only mirrors facing-the-camera state onto an attribute
      // if the hotspot opts in; without this it never sets data-visible and
      // the CSS below would hide every marker.
      b.dataset.visibilityAttribute = "visible";
      b.setAttribute("aria-label", p.label);
      var cap = document.createElement("span");
      cap.className = "caption";
      cap.textContent = p.label;
      b.appendChild(cap);
      b.addEventListener("click", function () {
        select(selected === p.node ? null : p.node, true);
      });
      mv.appendChild(b);
    });
    markHotspots();
  }

  function markHotspots() {
    Array.prototype.slice.call(mv.querySelectorAll(".hotspot")).forEach(function (h) {
      var node = h.slot.replace("hotspot-", "");
      h.dataset.selected = String(node === selected);
    });
  }

  function select(node, scrollIntoView) {
    selected = node;
    applySelection();
    markHotspots();
    var clear = document.getElementById("chip-isolate");
    clear.hidden = node === null;
    clear.setAttribute("aria-pressed", String(node !== null));
    if (tab !== "parts") { tab = "parts"; syncTabs(); }
    render();
    if (scrollIntoView && node) {
      // Selected from a hotspot: bring its row in the list into view.
      var el = panel.querySelector('[data-node="' + node + '"]');
      if (el) el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    } else if (node) {
      // Selected from the list: the highlight happens up in the 3D view, so
      // scroll back to it rather than leaving the user looking at text.
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  /* -------------------------------------------------------- panel UI */

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function render() {
    if (!data) return;
    if (tab === "parts") return renderParts();
    if (tab === "specs") return renderSpecs();
    return renderSafety();
  }

  function renderParts() {
    var html = '<p class="summary">' + esc(data.summary) + "</p>";
    html += '<div class="partlist">';
    data.parts.forEach(function (p) {
      if (!p.note) return;
      var open = selected === p.node;
      html +=
        '<button class="part" data-node="' + esc(p.node) + '" aria-expanded="' + open + '">' +
          '<span class="name">' + esc(p.label) + "</span>" +
          '<span class="arrow">' + (open ? "Highlighted" : "Show") + "</span>" +
          (open ? '<p class="note">' + esc(p.note) + "</p>" : "") +
        "</button>";
    });
    html += "</div>";
    html +=
      '<div class="hint"><strong>In AR:</strong> ' +
      esc(data.ar_tips.join(" ")) + "</div>";
    panel.innerHTML = html;

    Array.prototype.slice.call(panel.querySelectorAll(".part")).forEach(function (btn) {
      btn.addEventListener("click", function () {
        var node = btn.dataset.node;
        select(selected === node ? null : node, false);
      });
    });
  }

  function renderSpecs() {
    var html = '<table class="specs"><tbody>';
    data.specs.forEach(function (row) {
      html += "<tr><th>" + esc(row[0]) + "</th><td>" + esc(row[1]) + "</td></tr>";
    });
    html += "</tbody></table>";
    html +=
      '<div class="hint"><strong>Model envelope:</strong> ' +
      data.extents_m.length_z + " m long × " + data.extents_m.width_x +
      " m wide × " + data.extents_m.height_y + " m high (machine only). " +
      "Placed in AR at true 1:1.</div>";
    panel.innerHTML = html;
  }

  function renderSafety() {
    var html = '<ul class="safety">';
    data.safety.forEach(function (s) { html += "<li>" + esc(s) + "</li>"; });
    html += "</ul>";
    html +=
      '<div class="hint">These are teaching points, not a substitute for your ' +
      "site's Standard Operating Procedures, DGMS circulars or the statutory " +
      "training your crew must complete.</div>";
    panel.innerHTML = html;
  }

  function syncTabs() {
    Array.prototype.slice.call(document.querySelectorAll(".tab")).forEach(function (t) {
      t.setAttribute("aria-selected", String(t.dataset.tab === tab));
    });
  }

  Array.prototype.slice.call(document.querySelectorAll(".tab")).forEach(function (t) {
    t.addEventListener("click", function () {
      tab = t.dataset.tab;
      syncTabs();
      render();
    });
  });

  /* ---------------------------------------------------------- toolbar */

  document.getElementById("chip-figure").addEventListener("click", function () {
    figureOn = !figureOn;
    this.setAttribute("aria-pressed", String(figureOn));
    applyFigure();
  });

  document.getElementById("chip-isolate").addEventListener("click", function () {
    select(null, false);
  });

  document.getElementById("chip-reset").addEventListener("click", function () {
    mv.cameraOrbit = "-145deg 70deg 100%";
    mv.fieldOfView = "auto";
    mv.cameraTarget = "auto auto auto";
    select(null, false);
  });

  document.getElementById("chip-labels").addEventListener("click", function () {
    labelsOn = !labelsOn;
    this.setAttribute("aria-pressed", String(labelsOn));
    buildHotspots();
  });

  /* --------------------------------------------------- AR availability */

  mv.addEventListener("ar-status", function (ev) {
    if (ev.detail.status === "failed") {
      var note = document.createElement("div");
      note.className = "note";
      note.innerHTML =
        "<strong>AR session ended unexpectedly</strong>Move to a better-lit " +
        "area with more floor texture and try again.";
      panel.prepend(note);
    }
  });

  customElements.whenDefined("model-viewer").then(function () {
    setTimeout(function () {
      if (!mv.canActivateAR) {
        var b = document.getElementById("ar-btn");
        if (b) b.remove();
        var note = document.createElement("div");
        note.className = "note";
        note.innerHTML =
          "<strong>Floor AR is not available on this device</strong>" +
          "No ARCore here, so the model cannot be placed on the floor. You " +
          "can still spin and zoom it below — and Marker AR works on any " +
          "device with a camera." +
          '<div class="cta">' +
            '<a class="cta-main" href="marker.html">📷 Open Marker AR</a>' +
            '<a class="cta-alt" href="print-markers.html">Print the markers</a>' +
          "</div>";
        panel.prepend(note);
      }
    }, 1200);
  }).catch(function () {});
})();
