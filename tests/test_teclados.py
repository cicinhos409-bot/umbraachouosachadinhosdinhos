"""Teclados do bot_mestre e dos painéis: um jeito só de montar (teclados.py), e um teclado só para cada um repetido."""
import ast
import glob
import os

PASTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _botoes(teclado):
    return [[b.text for b in linha] for linha in teclado.keyboard]


def test_montar_teclado_fixa_embaixo_e_ajusta_o_tamanho(bm):
    teclado = bm.montar_teclado([[bm.KeyboardButton(text="A")]])
    assert teclado.resize_keyboard is True and teclado.is_persistent is True
    assert _botoes(bm.teclado_com_cancelar("Salvar ✅")) == [["Salvar ✅", "Cancelar ❌"]]
    assert _botoes(bm.teclado_aprovar_cancelar) == [["Aprovar ✅", "Cancelar ❌"]]
    assert _botoes(bm.teclado_janela_dia_todo) == [["Dia Todo (24h) 🕛"], ["Cancelar ❌"]]


def test_ninguem_monta_teclado_do_padrao_a_mao():
    # O padrão (fixo e ajustado) sai só do teclados.montar_teclado, no bot_mestre e nos
    # painéis em arquivo próprio: assim um ajuste vale para todos.
    fora = []
    for caminho in sorted(glob.glob(os.path.join(PASTA, "*.py"))):
        if os.path.basename(caminho) == "teclados.py":
            continue
        arvore = ast.parse(open(caminho, encoding="utf-8").read())
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and getattr(no.func, "id", None) == "ReplyKeyboardMarkup":
                nomes = sorted(k.arg for k in no.keywords)
                if nomes == ["is_persistent", "keyboard", "resize_keyboard"]:
                    fora.append(f"{os.path.basename(caminho)}:{no.lineno}")
    assert fora == [], "use teclados.montar_teclado: " + ", ".join(fora)


def test_paineis_usam_os_teclados_repetidos_do_mesmo_lugar(bm):
    import painel_shopee_video as sv
    import teclados
    assert bm.teclado_cancelar is teclados.teclado_cancelar is sv.teclado_cancelar
    assert bm.teclado_aprovar_cancelar is sv.teclado_aprovar_cancelar
    assert bm.teclado_janela_dia_todo is sv.teclado_janela_dia_todo
    for definicao in ("def montar_teclado(", "def teclado_com_cancelar(", "teclado_cancelar = ",
                      "teclado_aprovar_cancelar = ", "teclado_janela_dia_todo = "):
        for arquivo in ("bot_mestre.py", "painel_shopee_video.py", "painel_acessos.py",
                        "painel_notas.py", "painel_espelhos.py"):
            fonte = open(os.path.join(PASTA, arquivo), encoding="utf-8").read()
            assert "\n" + definicao not in fonte, f"{arquivo} tem a própria cópia de {definicao}"
