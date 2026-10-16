"""Painel de submissão do Grupo Público: um painel por membro, sem painel preso no tópico."""
import asyncio
from types import SimpleNamespace

from conftest import rodar

GRUPO = -1001
TOPICO = 7
NAY = SimpleNamespace(id=555, username="nay", first_name="Nay")


def _preparar(bm, monkeypatch):
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    enviados, apagados = [], []

    async def send_message(chat_id, texto, **k):
        enviados.append(texto)
        return SimpleNamespace(message_id=100 + len(enviados))

    async def delete_message(chat_id=None, message_id=None):
        apagados.append(message_id)
        return True

    async def edit_message_text(**k):
        return True

    monkeypatch.setattr(bm.bot, "send_message", send_message)
    monkeypatch.setattr(bm.bot, "delete_message", delete_message)
    monkeypatch.setattr(bm.bot, "edit_message_text", edit_message_text)
    monkeypatch.setattr(bm, "_travas_painel_membro", {}, raising=False)
    monkeypatch.setattr(bm, "criar_task", lambda coro: coro.close())  # sem cronômetro rodando
    dormir = asyncio.sleep
    monkeypatch.setattr(bm.asyncio, "sleep", lambda *_: dormir(0))
    estado = FSMContext(storage=bm.dp.storage, key=StorageKey(bot_id=bm.bot.id, chat_id=GRUPO,
                                                              user_id=NAY.id, thread_id=None))
    return enviados, apagados, estado


def _clique(dados):
    async def answer(*a, **k):
        pass

    async def edit_text(*a, **k):
        pass
    mensagem = SimpleNamespace(chat=SimpleNamespace(id=GRUPO), message_thread_id=TOPICO, edit_text=edit_text)
    return SimpleNamespace(from_user=NAY, data=dados, answer=answer, message=mensagem)


async def _painel(estado):
    return (await estado.get_data()).get("msg_wizard_id")


def _registro(bm):
    return [p["message_id"] for p in bm.db.ler_config("paineis_wizard_abertos", [])]


def test_tocar_iniciar_de_novo_troca_o_painel_em_vez_de_deixar_o_anterior_preso(bm, monkeypatch):
    # O Rafael notou em 16/10: painéis da Nay (15/10) e da Mari (12/10) parados no tópico,
    # com o cronômetro congelado. O botão fica sempre na barra da mensagem fixada e o
    # painel novo nasce no fim do tópico; cada toque deixava o anterior para trás.
    enviados, apagados, estado = _preparar(bm, monkeypatch)

    async def cenario():
        await estado.clear()
        await bm.wizard_abrir_painel(_clique("iniciar_wizard_oferta"), estado)
        primeiro = await _painel(estado)
        await bm.wizard_abrir_painel(_clique("iniciar_wizard_oferta"), estado)
        segundo = await _painel(estado)

        assert len(enviados) == 2 and primeiro != segundo
        assert apagados == [primeiro]
        assert _registro(bm) == [segundo]

    rodar(cenario())


def test_video_e_link_encaminhados_juntos_abrem_um_painel_so(bm, monkeypatch):
    enviados, apagados, estado = _preparar(bm, monkeypatch)
    link = "https://s.shopee.com.br/AbCdEf123"

    async def cenario():
        await estado.clear()
        await asyncio.gather(
            bm.criar_painel_submissao(GRUPO, TOPICO, NAY, estado, video_id="video_da_nay"),
            bm.criar_painel_submissao(GRUPO, TOPICO, NAY, estado, link_shopee=link),
        )
        dados = await estado.get_data()

        assert len(enviados) == 1 and apagados == []
        assert dados["video_file_id"] == "video_da_nay" and dados["link_shopee"] == link

    rodar(cenario())


def test_painel_cancelado_sai_do_registro_anti_orfao(bm, monkeypatch):
    # Painel que saiu do grupo não fica no registro: a varredura da próxima subida
    # tentaria apagá-lo de novo e encheria o teto de 200 com painéis que já não existem.
    _, apagados, estado = _preparar(bm, monkeypatch)

    async def cenario():
        await estado.clear()
        await bm.wizard_abrir_painel(_clique("iniciar_wizard_oferta"), estado)
        painel = await _painel(estado)
        await bm.wizard_cancelar(_clique(f"cancelar_wizard:{NAY.id}"), estado)

        assert apagados == [painel]
        assert _registro(bm) == []

    rodar(cenario())
