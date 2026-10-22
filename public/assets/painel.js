/*
 * Base compartilhada do painel web (protótipo). Carregue DEPOIS do HTML da página:
 *   <link rel="stylesheet" href="/assets/painel.css">
 *   <div class="wrap"><div id="topo"></div> ... </div>
 *   <script src="/assets/painel.js"></script>
 *
 * API (window.Painel):
 *   Painel.topo(idPagina)           desenha a barra lateral (menu deslizante no celular) e põe o aviso de protótipo dentro de #topo
 *   Painel.estado(chave, padrao)    estado salvo só neste navegador (localStorage), sempre com try/catch:
 *                                     .ler() -> objeto (padrao + o que foi salvo)
 *                                     .salvar(obj) -> grava
 *                                     .alterar(fn) -> fn(objeto) muda o objeto e grava
 *   Painel.confirmar(texto, aoConfirmar)   caixa Cancelar ❌ / Confirmar ✅ (cria a <dialog> sozinha)
 *   Painel.aviso(texto)             mensagem rápida no pé da tela (cria o #toast sozinho)
 *   Painel.soServidor(rotulo)       aviso padrão para ações que só funcionam com o servidor ligado
 *   Painel.esc(texto)               escapa HTML (use sempre ao pôr texto digitado em innerHTML)
 *   Painel.$(id) / Painel.$$(seletor)
 *   Painel.faixa(texto, maximo)     "6" ou "5-10" -> [piso, topo] ou null (mesma regra do painel do Telegram)
 *   Painel.janela(texto)            "13-22" ou "dia todo" -> [inicio, fim] ou null (0 <= inicio < fim <= 24)
 *   Painel.rotuloFaixa(p, t) / Painel.rotuloJanela(i, f)
 *
 * Nada aqui fala com o servidor: tudo fica no navegador de quem abriu a página.
 */
(function () {
  "use strict";

  // Todas as páginas do painel, na ordem do menu do bot. Cada id é o nome do arquivo em public/.
  // grupo = título da seção na barra lateral; sub = item recuado (fica dentro de outra área do bot).
  var PAGES = [
    { id: "painel", href: "/painel", nome: "Início", grupo: "" },
    { id: "canal-afiliados", href: "/canal-afiliados", nome: "Canal Afiliados 📺", grupo: "Menu inicial" },
    { id: "relatorios", href: "/relatorios", nome: "Relatório Geral 📊", grupo: "Menu inicial" },
    { id: "notas", href: "/notas", nome: "Disparador de Notas 🧾", grupo: "Menu inicial", sub: true },
    { id: "servidor", href: "/servidor", nome: "Opções do Servidor ⚙️", grupo: "Menu inicial" },
    { id: "espiao", href: "/espiao", nome: "Espião Afiliados 🕵️", grupo: "Outros Canais 🗂️" },
    { id: "espelhador", href: "/espelhador", nome: "Espelhador de Canais 🔄", grupo: "Outros Canais 🗂️" },
    { id: "autorais", href: "/autorais", nome: "Vídeos Autorais 🎥", grupo: "Outros Canais 🗂️" },
    { id: "publico", href: "/publico", nome: "Grupo Público 📬", grupo: "Outros Canais 🗂️" },
    { id: "parceiros", href: "/parceiros", nome: "Parceiros Afiliados 👥", grupo: "Outros Canais 🗂️", sub: true },
    { id: "achadinhos", href: "/achadinhos", nome: "Gerador de Achadinhos 🛍️", grupo: "Outros Canais 🗂️" },
    { id: "shopee-video", href: "/shopee-video", nome: "Shopee Vídeo 🎬", grupo: "Outros Canais 🗂️" }
  ];

  var $ = function (id) { return document.getElementById(id); };
  var $$ = function (sel, raiz) { return Array.prototype.slice.call((raiz || document).querySelectorAll(sel)); };

  function esc(texto) {
    return String(texto == null ? "" : texto).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function topo(idPagina) {
    var alvo = $("topo");
    if (!alvo || $("painel-side")) return;
    document.body.classList.add("com-painel");

    var atualPag = PAGES.filter(function (p) { return p.id === idPagina; })[0];
    var itens = "", grupoAtual = null;
    PAGES.forEach(function (p) {
      if (p.grupo && p.grupo !== grupoAtual) { itens += '<p class="grupo">' + esc(p.grupo) + "</p>"; }
      grupoAtual = p.grupo;
      itens += '<a class="item-menu' + (p.sub ? " sub" : "") + '" href="' + p.href + '"' +
        (p.id === idPagina ? ' aria-current="page"' : "") + ">" + esc(p.nome) + "</a>";
    });

    // Barra do alto (só no celular), a gaveta lateral e a película que escurece o resto.
    var barra = document.createElement("div");
    barra.className = "painel-topbar";
    barra.innerHTML = '<button type="button" id="painel-abrir" aria-controls="painel-side" aria-expanded="false" aria-label="Abrir o menu">☰ Menu</button>' +
      '<span class="titulo">' + esc(atualPag ? atualPag.nome : "Painel") + "</span>";
    var lateral = document.createElement("aside");
    lateral.id = "painel-side"; lateral.className = "painel-side"; lateral.setAttribute("aria-label", "Menu do painel");
    lateral.innerHTML = '<div class="painel-side-head"><a class="marca" href="/painel">🎛️ Painel do robô</a>' +
      '<button type="button" class="fechar" id="painel-fechar" aria-label="Fechar o menu">✕</button></div>' +
      '<div class="lista" role="navigation" aria-label="Painéis">' + itens + "</div>" +
      '<div class="painel-side-foot"><a href="/">← Visão geral do site</a></div>';
    var pelicula = document.createElement("div");
    pelicula.className = "painel-overlay"; pelicula.id = "painel-overlay";
    document.body.insertBefore(pelicula, document.body.firstChild);
    document.body.insertBefore(lateral, document.body.firstChild);
    document.body.insertBefore(barra, document.body.firstChild);

    alvo.innerHTML =
      '<div class="banner" role="note"><b>Protótipo da tela.</b> Este painel ainda não está ligado ao robô: ' +
      "o que você muda aqui fica só neste navegador e não altera nada no servidor nem no Telegram. " +
      "Números e nomes de exemplo estão marcados.</div>";

    var botaoAbrir = $("painel-abrir");
    function abrir() {
      lateral.classList.add("aberto"); pelicula.classList.add("on");
      botaoAbrir.setAttribute("aria-expanded", "true");
      var primeiro = lateral.querySelector("a.item-menu"); if (primeiro) primeiro.focus();
    }
    function fechar(devolverFoco) {
      lateral.classList.remove("aberto"); pelicula.classList.remove("on");
      botaoAbrir.setAttribute("aria-expanded", "false");
      if (devolverFoco) botaoAbrir.focus();
    }
    botaoAbrir.addEventListener("click", abrir);
    $("painel-fechar").addEventListener("click", function () { fechar(true); });
    pelicula.addEventListener("click", function () { fechar(true); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && lateral.classList.contains("aberto")) fechar(true);
    });

    // Mantém a rolagem da barra entre uma página e outra e deixa o item atual à vista.
    try { lateral.scrollTop = parseInt(sessionStorage.getItem("painel:side") || "0", 10) || 0; } catch (e) {}
    lateral.addEventListener("scroll", function () { try { sessionStorage.setItem("painel:side", String(lateral.scrollTop)); } catch (e) {} });
    var atual = lateral.querySelector('[aria-current="page"]');
    if (atual && atual.scrollIntoView) { try { atual.scrollIntoView({ block: "nearest" }); } catch (e) {} }
  }

  function estado(chave, padrao) {
    var k = "painel:" + chave;
    function ler() {
      try {
        var salvo = JSON.parse(localStorage.getItem(k) || "null");
        return salvo && typeof salvo === "object" ? Object.assign({}, JSON.parse(JSON.stringify(padrao)), salvo) : JSON.parse(JSON.stringify(padrao));
      } catch (e) { return JSON.parse(JSON.stringify(padrao)); }
    }
    function salvar(obj) { try { localStorage.setItem(k, JSON.stringify(obj)); } catch (e) {} }
    function alterar(fn) { var o = ler(); fn(o); salvar(o); return o; }
    return { ler: ler, salvar: salvar, alterar: alterar };
  }

  var dlg, dlgTexto, acaoPendente = null;
  function garantirDialogo() {
    if ($("dlg")) { dlg = $("dlg"); dlgTexto = $("dlg-texto"); return; }
    dlg = document.createElement("dialog");
    dlg.id = "dlg";
    dlg.setAttribute("aria-labelledby", "dlg-texto");
    dlg.innerHTML = '<p id="dlg-texto"></p><div class="actions">' +
      '<button type="button" id="dlg-nao">Cancelar ❌</button>' +
      '<button type="button" id="dlg-sim" class="primary">Confirmar ✅</button></div>';
    document.body.appendChild(dlg);
    dlgTexto = $("dlg-texto");
    $("dlg-nao").addEventListener("click", function () { acaoPendente = null; dlg.close(); });
    $("dlg-sim").addEventListener("click", function () { var f = acaoPendente; acaoPendente = null; dlg.close(); if (f) f(); });
  }
  function confirmar(texto, aoConfirmar) {
    garantirDialogo();
    dlgTexto.textContent = texto;
    acaoPendente = aoConfirmar;
    dlg.showModal();
  }

  var toastTimer;
  function aviso(texto) {
    var t = $("toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast"; t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite");
      document.body.appendChild(t);
    }
    t.textContent = texto; t.classList.add("on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("on"); }, 3800);
  }
  function soServidor(rotulo) {
    aviso('Protótipo: "' + rotulo + '" só funciona quando o painel for ligado ao servidor.');
  }

  // Mesmas regras do painel_shopee_video.py do bot.
  function faixa(texto, maximo) {
    var m = /^(\d{1,3})(?:\s*-\s*(\d{1,3}))?$/.exec((texto || "").trim());
    if (!m) return null;
    var piso = parseInt(m[1], 10), topoN = m[2] ? parseInt(m[2], 10) : piso;
    if (piso < 1 || topoN < piso || topoN > (maximo || 50)) return null;
    return [piso, topoN];
  }
  function janela(texto) {
    texto = (texto || "").trim();
    if (texto.toLowerCase() === "dia todo") return [0, 24];
    var m = /^(\d{1,2})\s*-\s*(\d{1,2})$/.exec(texto);
    if (!m) return null;
    var ini = parseInt(m[1], 10), fim = parseInt(m[2], 10);
    return (ini >= 0 && ini < fim && fim <= 24) ? [ini, fim] : null;
  }
  function rotuloFaixa(p, t) { return t > p ? p + " a " + t : p + " (fixo)"; }
  function rotuloJanela(i, f) { return (i === 0 && f === 24) ? "o dia todo (24h)" : "das " + i + "h às " + f + "h"; }

  window.Painel = {
    PAGES: PAGES, $: $, $$: $$, esc: esc, topo: topo, estado: estado,
    confirmar: confirmar, aviso: aviso, soServidor: soServidor,
    faixa: faixa, janela: janela, rotuloFaixa: rotuloFaixa, rotuloJanela: rotuloJanela
  };
})();
