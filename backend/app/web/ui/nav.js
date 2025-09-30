// --- tiny nav helper -------------------------------------------------
(function () {
  const css = `
  .topnav-wrap{position:sticky;top:0;z-index:50;background:#0b1220;border-bottom:1px solid #1f2937}
  .topnav{max-width:1200px;margin:0 auto;padding:10px 16px;display:flex;align-items:center;gap:12px}
  .brand{font-weight:800;letter-spacing:.3px}
  .nav-links{display:flex;gap:10px;flex-wrap:wrap}
  .nav-links a{display:inline-block;padding:8px 10px;border-radius:8px;border:1px solid #1f2937;background:#111827;color:#e5e7eb;text-decoration:none}
  .nav-links a.active{outline:2px solid #22c55e}
  .nav-right{margin-left:auto;display:flex;gap:8px;align-items:center}
  .nav-input{padding:8px 10px;border-radius:8px;border:1px solid #1f2937;background:#0f172a;color:#e5e7eb;min-width:260px}
  .nav-btn{padding:8px 12px;border-radius:8px;border:1px solid #1f2937;background:#1f2937;color:#fff;cursor:pointer}
  .nav-btn:hover{filter:brightness(1.1)}
  `;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  function getParam(name){
    const u=new URL(location.href);
    return u.searchParams.get(name)||"";
  }
  function setParamInUrl(url, key, val){
    const u=new URL(url, location.origin);
    if(val) u.searchParams.set(key, val); else u.searchParams.delete(key);
    return u.pathname + u.searchParams.toString().replace(/^/,'?').replace(/\?$/,'');
  }

  function currentUserId(userInputId){
    const el = userInputId ? document.getElementById(userInputId) : null;
    const v = el && el.value ? el.value.trim() : "";
    return v || getParam("user_id");
  }

  function buildLinks(uid){
    return [
      { key: "editor",    text: "Редактор",   href: setParamInUrl("/ui/portfolio_editor.html",   "user_id", uid) },
      { key: "snapshot",  text: "Снапшот",    href: setParamInUrl("/ui/portfolio_snapshot.html", "user_id", uid) },
      { key: "valuations",text: "Оценки EOD", href: setParamInUrl("/ui/valuations.html",         "user_id", uid) },
      { key: "ai",        text: "AI-оценка",  href: setParamInUrl("/ui/portfolio_ai.html",       "user_id", uid) },
    ];
  }

  function renderNav(activeKey, opts){
    opts = opts || {};
    const userInputId = opts.userInputId; // id поля на странице, если есть
    const mountId = opts.mountId || "topnav";
    const mount = document.getElementById(mountId) || (function(){
      const d=document.createElement("div"); d.id=mountId; document.body.prepend(d); return d;
    })();

    let uid = currentUserId(userInputId);
    const links = buildLinks(uid);

    // html
    mount.innerHTML = `
      <div class="topnav-wrap">
        <div class="topnav">
          <div class="brand">AI Portfolio</div>
          <nav class="nav-links">
            ${links.map(l => `<a href="${l.href}" data-key="${l.key}" class="${l.key===activeKey?'active':''}">${l.text}</a>`).join("")}
          </nav>
          <div class="nav-right">
            <input id="navUser" class="nav-input" placeholder="user_id" value="${uid||""}" />
            <button id="navGo" class="nav-btn">Go</button>
          </div>
        </div>
      </div>
    `;

    // логика
    const navUser = document.getElementById("navUser");
    const navGo = document.getElementById("navGo");
    const refreshLinks = ()=>{
      const val = navUser.value.trim();
      document.querySelectorAll('.nav-links a').forEach(a=>{
        a.setAttribute("href", setParamInUrl(a.getAttribute("href"), "user_id", val));
      });
    };
    navUser.addEventListener("input", refreshLinks);
    navGo.addEventListener("click", ()=>{ 
      const self = document.querySelector(`.nav-links a[data-key="${activeKey}"]`);
      location.href = self ? self.getAttribute("href") : setParamInUrl(location.href,"user_id",navUser.value.trim());
    });

    // синхронизация с полем страницы (если есть)
    const pageInput = userInputId ? document.getElementById(userInputId) : null;
    if(pageInput){
      if(!navUser.value && pageInput.value) { navUser.value = pageInput.value; refreshLinks(); }
      pageInput.addEventListener("input", ()=>{ navUser.value = pageInput.value; refreshLinks(); });
      navUser.addEventListener("input", ()=>{ pageInput.value = navUser.value; });
    }
  }

  // экспорт
  window.renderNav = renderNav;
})();




