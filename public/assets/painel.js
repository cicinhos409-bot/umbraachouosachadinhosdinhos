/*
 * Base compartilhada do painel web (protótipo). Carregue DEPOIS do HTML da página:
 *   <link rel="stylesheet" href="/assets/painel.css">
 *   <div class="wrap"><div id="topo"></div> ... </div>
 *   <script src="/assets/painel.js"></script>
 *
 * API (window.Painel):
 *   Painel.topo(idPagina)           desenha a navegação entre painéis e o aviso de protótipo dentro de #topo
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
  var PAGES = [
    { id: "painel", href: "/painel", nome: "Início" },
    { id: "canal-afiliados", href: "/canal-afiliados", nome: "Canal Afiliados 📺" },
    { id: "espiao", href: "/espiao", nome: "Espião 🕵️" },
    { id: "espelhador", href: "/espelhador", nome: "Espelhador 🔄" },
    { id: "autorais", href: "/autorais", nome: "Autorais 🎥" },
    { id: "publico", href: "/publico", nome: "Grupo Público 📬" },
    { id: "parceiros", href: "/parceiros", nome: "Parceiros 👥" },
    { id: "achadinhos", href: "/achadinhos", nome: "Achadinhos 🛍️" },
    { id: "shopee-video", href: "/shopee-video", nome: "Shopee Vídeo 🎬" },
    { id: "relatorios", href: "/relatorios", nome: "Relatórios 📊" },
    { id: "notas", href: "/notas", nome: "Notas 🧾" },
    { id: "servidor", href: "/servidor", nome: "Servidor ⚙️" }
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
    if (!alvo) return;
    var links = PAGES.map(function (p) {
      return '<a href="' + p.href + '"' + (p.id === idPagina ? ' aria-current="page"' : "") + ">" + esc(p.nome) + "</a>";
    }).join("");
    alvo.innerHTML =
      '<nav class="painel-nav" aria-label="Painéis">' + links + "</nav>" +
      '<div class="banner" role="note"><b>Protótipo da tela.</b> Este painel ainda não está ligado ao robô: ' +
      "o que você muda aqui fica só neste navegador e não altera nada no servidor nem no Telegram. " +
      "Números e nomes de exemplo estão marcados.</div>";
    var atual = alvo.querySelector('[aria-current="page"]');
    if (atual && atual.scrollIntoView) { try { atual.scrollIntoView({ inline: "center", block: "nearest" }); } catch (e) {} }
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
