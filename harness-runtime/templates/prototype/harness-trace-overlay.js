/*
 * harness-trace-overlay.js — 原型 trace 脊柱可视层（dev-only）
 *
 * 用途：走查原型时，让人直观看到"当前这屏 / 这个区域对应哪个界面边界(SURF)、
 *       哪个系统用例(SUC)、承载哪个业务对象(OBJ)"。读 DOM 上的
 *       data-surf / data-suc / data-obj 锚点，叠加 badge，并提供侧栏汇总。
 *
 * 接入：在原型页面引入本脚本（开发态），按 T 键或加 ?trace=1 开关。
 *       <script src="/harness-trace-overlay.js" defer></script>
 *       它不渲染生产 UI，只在 trace 模式下注入覆盖层；关闭后无残留。
 *
 * 约束：纯展示，不修改业务 DOM；ID 引用上游真源，不在此处定义或改写。
 */
(function () {
  "use strict";

  var STYLE_ID = "harness-trace-overlay-style";
  var PANEL_ID = "harness-trace-overlay-panel";
  var BADGE_CLASS = "harness-trace-badge";
  var active = false;

  function qsAll(sel) {
    return Array.prototype.slice.call(document.querySelectorAll(sel));
  }

  function tracedElements() {
    return qsAll("[data-surf],[data-suc],[data-obj]");
  }

  function labelFor(el) {
    var parts = [];
    if (el.getAttribute("data-surf")) parts.push(el.getAttribute("data-surf"));
    if (el.getAttribute("data-suc")) parts.push(el.getAttribute("data-suc"));
    if (el.getAttribute("data-obj")) parts.push("⬡ " + el.getAttribute("data-obj"));
    return parts.join(" · ");
  }

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      "[data-harness-traced]{outline:1px dashed rgba(99,102,241,.7) !important;outline-offset:1px;}",
      "." + BADGE_CLASS + "{position:absolute;z-index:2147483646;font:11px/1.4 ui-monospace,monospace;",
      "background:#4338ca;color:#fff;padding:1px 6px;border-radius:0 0 6px 0;pointer-events:none;white-space:nowrap;}",
      "#" + PANEL_ID + "{position:fixed;right:12px;bottom:12px;z-index:2147483647;max-width:320px;max-height:50vh;",
      "overflow:auto;background:#111827;color:#e5e7eb;font:12px/1.5 ui-monospace,monospace;border-radius:8px;",
      "box-shadow:0 6px 24px rgba(0,0,0,.35);padding:10px 12px;}",
      "#" + PANEL_ID + " h4{margin:0 0 6px;font-size:12px;color:#a5b4fc;}",
      "#" + PANEL_ID + " .row{padding:2px 0;border-top:1px solid #1f2937;}",
      "#" + PANEL_ID + " .k{color:#93c5fd;}",
    ].join("\n");
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = css;
    document.head.appendChild(style);
  }

  function clearOverlay() {
    qsAll("." + BADGE_CLASS).forEach(function (b) { b.remove(); });
    qsAll("[data-harness-traced]").forEach(function (el) { el.removeAttribute("data-harness-traced"); });
    var panel = document.getElementById(PANEL_ID);
    if (panel) panel.remove();
  }

  function renderOverlay() {
    clearOverlay();
    ensureStyle();
    var els = tracedElements();
    var surfs = {}, sucs = {}, objs = {};
    els.forEach(function (el) {
      el.setAttribute("data-harness-traced", "1");
      var rect = el.getBoundingClientRect();
      var badge = document.createElement("div");
      badge.className = BADGE_CLASS;
      badge.textContent = labelFor(el) || "(no id)";
      badge.style.top = (window.scrollY + rect.top) + "px";
      badge.style.left = (window.scrollX + rect.left) + "px";
      document.body.appendChild(badge);
      (el.getAttribute("data-surf") || "").split(/[ ,]+/).forEach(function (v) { if (v) surfs[v] = 1; });
      (el.getAttribute("data-suc") || "").split(/[ ,]+/).forEach(function (v) { if (v) sucs[v] = 1; });
      (el.getAttribute("data-obj") || "").split(/[ ,]+/).forEach(function (v) { if (v) objs[v] = 1; });
    });
    var panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.innerHTML =
      "<h4>Trace 脊柱（按 T 关闭）</h4>" +
      "<div class='row'><span class='k'>SURF</span> " + Object.keys(surfs).sort().join(", ") + "</div>" +
      "<div class='row'><span class='k'>SUC</span> " + Object.keys(sucs).sort().join(", ") + "</div>" +
      "<div class='row'><span class='k'>OBJ</span> " + Object.keys(objs).sort().join(", ") + "</div>" +
      "<div class='row' style='color:#6b7280'>" + els.length + " 个带锚点区域</div>";
    document.body.appendChild(panel);
  }

  function toggle(force) {
    active = typeof force === "boolean" ? force : !active;
    if (active) renderOverlay(); else clearOverlay();
  }

  document.addEventListener("keydown", function (e) {
    if ((e.key === "t" || e.key === "T") && !/input|textarea|select/i.test((e.target.tagName || ""))) {
      toggle();
    }
  });
  window.addEventListener("resize", function () { if (active) renderOverlay(); });
  window.addEventListener("scroll", function () { if (active) renderOverlay(); }, { passive: true });

  if (/[?&]trace=1\b/.test(location.search)) {
    if (document.readyState !== "loading") toggle(true);
    else document.addEventListener("DOMContentLoaded", function () { toggle(true); });
  }
})();
