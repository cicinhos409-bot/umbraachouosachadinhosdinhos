"""
Administradores: roteador do bot_mestre (Opções do Servidor → Administradores 🛡️).

Mostra, no privado do Rafael, o registro que a conta principal monta todo dia
(registro_admins): cada grupo e canal em que ele é dono ou admin, quem são os
administradores, o que cada um pode fazer, e as últimas mudanças. O aviso no privado
quando algo muda sai do bot_mestre (avisar_mudancas), a cada 15 min.
Decisão do Rafael: DECISOES.md, Monitor, deploy e servidor.
"""
import logging

from aiogram import Router, Bot, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton

import links_grupos
import registro_admins
from teclados import montar_teclado

logger = logging.getLogger("Painel_Admins")

router = Router()
bot_instance = None
ADMIN_ID = None

BOTAO = "Administradores 🛡️"
# Tratado no bot_mestre, junto do botão Opções do Servidor ⚙️, dono daquele teclado.
VOLTAR = "Voltar às Opções do Servidor 🔙"
LIMITE_LINHAS_AVISO = 30


def configurar_dependencias(bot: Bot, admin_id):
    global bot_instance, ADMIN_ID
    bot_instance, ADMIN_ID = bot, admin_id


def teclado_painel():
    return montar_teclado([[KeyboardButton(text=VOLTAR)]])


@router.message(F.text == BOTAO, StateFilter("*"))
async def painel_handler(message: types.Message, state: FSMContext):
    if message.from_user is None or message.from_user.id != ADMIN_ID:
        return
    await state.clear()
    logger.info("🛡️ Consultando o registro de administradores.")
    textos = registro_admins.textos_do_painel(links_grupos.nome_clicavel)
    for i, texto in enumerate(textos):
        teclado = teclado_painel() if i == len(textos) - 1 else None
        await message.answer(texto, parse_mode="HTML", reply_markup=teclado, disable_web_page_preview=True)


def texto_do_aviso(mudancas):
    """O aviso no privado com as mudanças novas (as primeiras LIMITE_LINHAS_AVISO)."""
    linhas = [registro_admins.linha_mudanca(m, links_grupos.nome_clicavel) for m in mudancas[:LIMITE_LINHAS_AVISO]]
    texto = "🛡️ <b>Administradores: o que mudou</b>\n\n" + "\n".join(linhas)
    if len(mudancas) > LIMITE_LINHAS_AVISO:
        texto += f"\n\n…e mais {len(mudancas) - LIMITE_LINHAS_AVISO}."
    return texto + f"\n\n<i>O registro completo fica em Opções do Servidor ⚙️ → {BOTAO}.</i>"


async def avisar_mudancas():
    """Manda no privado as mudanças que a conferência achou e ainda não foram avisadas."""
    try:
        mudancas = registro_admins.mudancas_nao_avisadas()
        if not mudancas:
            return
        await bot_instance.send_message(ADMIN_ID, texto_do_aviso(mudancas), parse_mode="HTML",
                                        disable_web_page_preview=True)
        registro_admins.marcar_avisadas([m["id"] for m in mudancas])
        logger.info(f"🛡️ Aviso de {len(mudancas)} mudança(s) de administradores enviado ao admin.")
    except Exception as e:
        logger.error(f"❌ [Admins] Falha ao avisar as mudanças: {type(e).__name__}: {e}")
