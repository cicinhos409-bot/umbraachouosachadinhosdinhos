"""
Teclados fixos embaixo da conversa, no padrão de todos os painéis do bot principal:
o bot_mestre e os painéis em arquivo próprio (Espelhador, Notas, Shopee Vídeo e
Acessos do Servidor). Um ajuste aqui vale para todos. O tests/test_teclados.py
barra teclado do padrão montado à mão.

- montar_teclado(linhas): o teclado fixo e ajustado ao tamanho dos botões.
- teclado_com_cancelar(texto): um botão de confirmar ao lado do Cancelar ❌.
- teclado_cancelar, teclado_aprovar_cancelar e teclado_janela_dia_todo: os que
  vários painéis usam iguais, para o texto de um botão mudar em todos.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def montar_teclado(linhas):
    """Teclado fixo embaixo da conversa, no padrão de todos os painéis do bot."""
    return ReplyKeyboardMarkup(keyboard=linhas, resize_keyboard=True, is_persistent=True)


def teclado_com_cancelar(texto_botao):
    """Um botão de confirmar (texto_botao) ao lado do Cancelar ❌."""
    return montar_teclado([[KeyboardButton(text=texto_botao), KeyboardButton(text="Cancelar ❌")]])


teclado_cancelar = montar_teclado([[KeyboardButton(text="Cancelar ❌")]])
teclado_aprovar_cancelar = teclado_com_cancelar("Aprovar ✅")
teclado_janela_dia_todo = montar_teclado([[KeyboardButton(text="Dia Todo (24h) 🕛")], [KeyboardButton(text="Cancelar ❌")]])
