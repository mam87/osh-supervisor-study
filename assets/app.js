// ===== Shared site logic: theme, search, data loading, arabic normalization =====

const AR_DIGITS = "٠١٢٣٤٥٦٧٨٩";
function normalizeAr(s){
  if(!s) return "";
  return s
    .replace(/[إأآا]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .replace(/ؤ/g, "و")
    .replace(/ئ/g, "ي")
    .replace(/[ً-ْـ]/g, "") // tashkeel + tatweel
    .replace(/[٠-٩]/g, d => String(AR_DIGITS.indexOf(d))) // arabic-indic -> western digits
    .toLowerCase()
    .trim();
}

function dataUrl(path){
  // resolve relative to /data/ from any page depth
  return basePath() + "data/" + path;
}
function basePath(){
  // pages live at root; unit.html etc. also at root. Keep simple.
  return "";
}

async function loadJSON(path){
  const res = await fetch(dataUrl(path), {cache: "force-cache"});
  if(!res.ok) throw new Error("failed to load " + path);
  return res.json();
}

// ---------- Theme ----------
(function initTheme(){
  const saved = localStorage.getItem("osh-theme");
  if(saved === "dark" || saved === "light"){
    document.documentElement.setAttribute("data-theme", saved);
  }
})();
function toggleTheme(){
  const cur = document.documentElement.getAttribute("data-theme");
  const isDark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const next = isDark ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try{ localStorage.setItem("osh-theme", next); }catch(e){}
}

// ---------- Global header search ----------
let __searchIndexPromise = null;
function getSearchIndex(){
  if(!__searchIndexPromise) __searchIndexPromise = loadJSON("search-index.json");
  return __searchIndexPromise;
}

function initHeaderSearch(){
  const input = document.getElementById("globalSearch");
  const box = document.getElementById("searchResults");
  if(!input || !box) return;

  let debounce = null;
  input.addEventListener("input", () => {
    clearTimeout(debounce);
    const q = input.value.trim();
    if(q.length < 2){ box.classList.remove("open"); box.innerHTML = ""; return; }
    debounce = setTimeout(() => runSearch(q, box), 150);
  });
  input.addEventListener("focus", () => { if(input.value.trim().length >= 2) box.classList.add("open"); });
  document.addEventListener("click", (e) => {
    if(!box.contains(e.target) && e.target !== input) box.classList.remove("open");
  });
  input.addEventListener("keydown", (e) => { if(e.key === "Escape"){ box.classList.remove("open"); input.blur(); } });
}

async function runSearch(q, box){
  const idx = await getSearchIndex();
  const nq = normalizeAr(q);
  const terms = nq.split(/\s+/).filter(Boolean);
  const scored = [];
  for(const item of idx){
    const hay = normalizeAr(item.heading + " " + item.eyebrow + " " + item.text);
    let score = 0;
    let allMatch = true;
    for(const t of terms){
      if(hay.includes(t)){
        score += (item.heading && normalizeAr(item.heading).includes(t)) ? 3 : 1;
      } else { allMatch = false; }
    }
    if(allMatch) scored.push({item, score});
  }
  scored.sort((a,b) => b.score - a.score);
  const top = scored.slice(0, 12);
  if(top.length === 0){
    box.innerHTML = '<div class="sr-empty">لا توجد نتائج لـ "' + escapeHtml(q) + '"</div>';
    box.classList.add("open");
    return;
  }
  box.innerHTML = top.map(({item}) => {
    const snippet = makeSnippet(item.text, terms);
    return `<a class="sr-item" href="unit.html?u=${item.unit}#slide-${item.slide}">
      <div class="sr-unit">الوحدة ${item.unit} — ${escapeHtml(item.unitTitle)}</div>
      <div class="sr-title">${escapeHtml(item.heading || item.eyebrow || "—")}</div>
      <div class="sr-snippet">${snippet}</div>
    </a>`;
  }).join("");
  box.classList.add("open");
}

function makeSnippet(text, terms){
  const nText = normalizeAr(text);
  let pos = -1;
  for(const t of terms){ const p = nText.indexOf(t); if(p >= 0){ pos = p; break; } }
  let start = Math.max(0, (pos >= 0 ? pos : 0) - 40);
  let snippet = text.slice(start, start + 160);
  if(start > 0) snippet = "… " + snippet;
  if(start + 160 < text.length) snippet = snippet + " …";
  return highlightTerms(escapeHtml(snippet), terms);
}

function highlightTerms(html, terms){
  // best-effort literal highlight (post-escape) for readability; normalization handled search matching separately
  let out = html;
  for(const t of terms){
    if(t.length < 2) continue;
    try{
      const re = new RegExp("(" + escapeRegex(t) + ")", "gi");
      out = out.replace(re, "<mark>$1</mark>");
    }catch(e){}
  }
  return out;
}
function escapeRegex(s){ return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

// ---------- Mobile nav ----------
function initMobileNav(){
  const btn = document.getElementById("hamburger");
  const nav = document.getElementById("topNav");
  if(!btn || !nav) return;
  btn.addEventListener("click", () => nav.classList.toggle("open"));
}

document.addEventListener("DOMContentLoaded", () => {
  initHeaderSearch();
  initMobileNav();
  const themeBtn = document.getElementById("themeToggle");
  if(themeBtn) themeBtn.addEventListener("click", toggleTheme);
});
