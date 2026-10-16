"""Registro dos administradores dos grupos e canais do Rafael: foto do dia, mudanças, painel e aviso."""
from datetime import datetime
from types import SimpleNamespace

import pytest

from conftest import rodar


class ChannelParticipantCreator:
    def __init__(self, rank=None):
        self.rank, self.admin_rights, self.promoted_by = rank, None, None


class ChannelParticipantAdmin:
    def __init__(self, promoted_by=None, rank=None, **direitos):
        self.rank, self.promoted_by = rank, promoted_by
        self.admin_rights = SimpleNamespace(**direitos)


class ChannelParticipant:
    pass


RAFAEL = 1226920464


def pessoa(user_id, nome, participante, usuario=None, bot=False):
    return SimpleNamespace(id=user_id, first_name=nome, last_name=None, username=usuario, bot=bot,
                           deleted=False, participant=participante)


def dialogo(chat_id, titulo, canal=True, dono=True, admin=False, usuario=False):
    entidade = SimpleNamespace(title=titulo, broadcast=canal, creator=dono, left=False,
                               admin_rights=SimpleNamespace(post_messages=True) if admin else None)
    return SimpleNamespace(id=chat_id, is_user=usuario, is_group=not canal and not usuario,
                           is_channel=canal and not usuario, entity=entidade)


class Conta:
    """Cliente do Telethon falso: as conversas da conta e os admins de cada uma."""

    def __init__(self, conversas):
        self.conversas = conversas        # [(dialogo, [pessoas])]

    async def iter_dialogs(self):
        for d, _ in self.conversas:
            yield d

    async def iter_participants(self, entidade, filter=None):
        for d, pessoas in self.conversas:
            if d.entity is entidade:
                for p in pessoas:
                    yield p


def _viral(com_downloader=True, bot_apaga=True):
    pessoas = [pessoa(RAFAEL, "Rafael", ChannelParticipantCreator(), "Rafaelnm"),
               pessoa(8707808275, "Shopee Vídeo Bot", ChannelParticipantAdmin(
                   promoted_by=RAFAEL, post_messages=True, edit_messages=True, delete_messages=bot_apaga,
                   ban_users=True, invite_users=True), "ShopeeVbot", bot=True)]
    if com_downloader:
        pessoas.append(pessoa(777, "Shopee Downloader", ChannelParticipantAdmin(promoted_by=RAFAEL), "BaixadorBot", bot=True))
    return (dialogo(-1003932482573, "Acervo Viral Shopee"), pessoas)


@pytest.fixture
def ra():
    import registro_admins
    return registro_admins


def test_primeira_conferencia_grava_a_foto_sem_avisar(ra):
    conta = Conta([_viral(),
                   (dialogo(-100555, "Grupo onde sou só membro", canal=False, dono=False), []),
                   (dialogo(42, "Conversa com alguém", usuario=True), [])])
    mudancas = ra.gravar(rodar(ra.coletar(conta)), datetime(2026, 10, 17, 4, 20))
    assert mudancas == [] and ra.mudancas_nao_avisadas() == []

    painel = "\n".join(ra.textos_do_painel())
    assert "1 grupo(s) e canal(is)" in painel and "3 administradores" in painel
    assert "Acervo Viral Shopee" in painel and "Grupo onde sou só membro" not in painel
    assert "👑 Rafael (@Rafaelnm): dono, pode tudo" in painel
    assert ("🤖 Shopee Vídeo Bot (@ShopeeVbot): postar mensagens, editar mensagens de outros, apagar mensagens "
            "de outros, banir usuários, convidar via link · promovido por Rafael") in painel
    assert "🤖 Shopee Downloader (@BaixadorBot): nenhuma permissão" in painel


def test_mudancas_de_um_dia_para_o_outro_viram_aviso(ra):
    antigo = (dialogo(-100900, "Grupo Antigo", canal=False), [pessoa(RAFAEL, "Rafael", ChannelParticipantCreator())])
    ra.gravar(rodar(ra.coletar(Conta([_viral(), antigo]))))
    novo = pessoa(555, "Ana", ChannelParticipantAdmin(promoted_by=RAFAEL, ban_users=True))
    viral = _viral(com_downloader=False, bot_apaga=False)
    viral[1].append(novo)
    mudancas = ra.gravar(rodar(ra.coletar(Conta([viral]))))
    textos = [m[3] for m in mudancas]
    assert "virou admin" in textos and "deixou de ser admin" in textos
    assert "permissões mudaram (perdeu: apagar mensagens de outros)" in textos
    assert any(t.startswith("saiu do registro") for t in textos)

    pendentes = ra.mudancas_nao_avisadas()
    assert len(pendentes) == 4
    ra.marcar_avisadas([m["id"] for m in pendentes])
    assert ra.mudancas_nao_avisadas() == []
    assert "Últimas mudanças" in ra.textos_do_painel()[-1]


def test_painel_grande_sai_em_varias_mensagens(ra):
    conversas = [(dialogo(-100000 - i, f"Grupo {i:02d}", canal=False),
                  [pessoa(RAFAEL, "Rafael", ChannelParticipantCreator(), "Rafaelnm")] +
                  [pessoa(1000 + j, f"Admin {j}", ChannelParticipantAdmin(post_messages=True, ban_users=True))
                   for j in range(8)]) for i in range(30)]
    ra.gravar(rodar(ra.coletar(Conta(conversas))))
    textos = ra.textos_do_painel(limite=3800)
    assert len(textos) > 1 and all(len(t) <= 3800 for t in textos)
    assert sum(t.count("👥 <b>Grupo") for t in textos) == 30


def test_ao_subir_so_confere_se_a_ultima_e_velha(ra, monkeypatch):
    chamadas = []

    async def conferir(client):
        chamadas.append(client)

    monkeypatch.setattr(ra, "conferir", conferir)
    rodar(ra.conferir_se_atrasado("conta", espera_s=0))
    assert chamadas == ["conta"]                                   # nunca conferiu
    ra.inicializar_tabelas()
    ra.db.salvar_config(ra.CHAVE_RESUMO, {"ultima": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    rodar(ra.conferir_se_atrasado("conta", espera_s=0))
    assert chamadas == ["conta"]                                   # conferiu agora há pouco


def test_bot_mostra_o_painel_e_avisa_as_mudancas(bm, Msg, Est, monkeypatch, ra):
    import painel_admins
    textos_teclado = [b.text for linha in bm.obter_teclado_opcoes_servidor().keyboard for b in linha]
    assert painel_admins.BOTAO in textos_teclado

    ra.gravar(rodar(ra.coletar(Conta([_viral()]))))
    msg = Msg(painel_admins.BOTAO)
    rodar(painel_admins.painel_handler(msg, Est()))
    assert "Acervo Viral Shopee" in msg.saidas[0]

    ra.gravar(rodar(ra.coletar(Conta([_viral(com_downloader=False)]))))
    enviadas = []

    async def send_message(chat_id, texto, **k):
        enviadas.append((chat_id, texto))

    monkeypatch.setattr(bm.bot, "send_message", send_message)
    rodar(painel_admins.avisar_mudancas())
    rodar(painel_admins.avisar_mudancas())                         # a mesma mudança não é avisada de novo
    assert len(enviadas) == 1 and enviadas[0][0] == bm.ADMIN_ID
    assert "<b>Shopee Downloader</b> deixou de ser admin" in enviadas[0][1]
