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


def _publicar_oferta(bm, monkeypatch, membro):
    """Membro conclui a oferta pelo painel; devolve a legenda publicada na Vídeos da Comunidade."""
    _, _, estado = _preparar(bm, monkeypatch)
    bm.salvar_submissao_config({**bm.ler_submissao_config(), "grupo_id": GRUPO, "topico_envio": TOPICO,
                                "topico_destino": 5})
    legendas = []

    async def get_file(file_id):
        return SimpleNamespace(file_path="videos/oferta.mp4")

    async def download_file(caminho, destination=None):
        with open(destination, "wb") as arquivo:
            arquivo.write(b"video")

    async def analisar(*a, **k):
        return "[APROVADO]\nTênis Casual Feminino 👟\n#SapatosFemininos"

    async def send_video(chat_id=None, video=None, caption=None, **k):
        legendas.append(caption)
        return SimpleNamespace(message_id=50)

    async def nada(*a, **k):
        return None

    monkeypatch.setattr(bm.bot, "get_file", get_file)
    monkeypatch.setattr(bm.bot, "download_file", download_file)
    monkeypatch.setattr(bm.bot, "send_video", send_video)
    monkeypatch.setattr(bm, "analisar_video_gemini", analisar)
    monkeypatch.setattr(bm, "reenviar_botao_ofertas", nada)

    async def cenario():
        await estado.clear()
        await bm.criar_painel_submissao(GRUPO, TOPICO, membro, estado, video_id="video_1",
                                        link_shopee="https://s.shopee.com.br/AbCdEf123")
        clique = _clique(f"wz_concluir:{membro.id}")
        clique.from_user = membro
        await bm.wizard_publicar_oferta(clique, estado)

    rodar(cenario())
    assert len(legendas) == 1
    return legendas[0]


def test_oferta_do_membro_sai_com_o_arroba_de_quem_postou(bm, monkeypatch):
    # Regra do Rafael (16/10): na Vídeos da Comunidade aparece o @ de quem postou.
    legenda = _publicar_oferta(bm, monkeypatch, NAY)
    assert legenda.startswith("👤 Vídeo enviado por: @nay\n\n<b>Tênis Casual Feminino 👟</b>")


def test_membro_sem_arroba_sai_com_o_nome_clicavel(bm, monkeypatch):
    mari = SimpleNamespace(id=777, username=None, first_name="Mari")
    legenda = _publicar_oferta(bm, monkeypatch, mari)
    assert legenda.startswith("👤 Vídeo enviado por: <a href='tg://user?id=777'>Mari</a>\n\n")
