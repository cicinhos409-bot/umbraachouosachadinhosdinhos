"""links_grupos: o nome do grupo nos painéis vira atalho para abrir o grupo no Telegram."""
from types import SimpleNamespace

from telethon.tl.types import Chat, ChatPhotoEmpty

import links_grupos as lg
from conftest import rodar


def _guardados():
    return {
        "-1001111": {"usuario": "achados_br", "convite": None, "ultima_msg": 50},
        "-1002222": {"usuario": None, "convite": None, "ultima_msg": 987},
        "-1003333": {"usuario": None, "convite": None, "ultima_msg": None},
        "-5232187113": {"usuario": None, "convite": "https://t.me/+convite_teste", "ultima_msg": 7},
    }


def test_link_de_cada_tipo_de_grupo():
    g = _guardados()
    assert lg.link("@achadosshopeebra", g) == "https://t.me/achadosshopeebra"
    assert lg.link("https://t.me/achadosshopeebra", g) == "https://t.me/achadosshopeebra"
    assert lg.link("https://t.me/+convite_direto", g) == "https://t.me/+convite_direto"
    # Salvo pelo número, mas o Telegram contou o @: abre para qualquer um.
    assert lg.link("-1001111", g) == "https://t.me/achados_br"
    assert lg.link("-1001111:5", g) == "https://t.me/achados_br/5"
    # Privado: abre na última mensagem; com tópico, no tópico.
    assert lg.link("-1002222", g) == "https://t.me/c/2222/987"
    assert lg.link("-1003333_12", g) == "https://t.me/c/3333/12"
    assert lg.link("-1003333", g) is None
    # Grupo comum: só com convite.
    assert lg.link("-5232187113", g) == "https://t.me/+convite_teste"
    assert lg.link("-4000000000", g) is None
    assert lg.link("Não definido", g) is None and lg.link(None, g) is None


def test_nome_clicavel_escapa_o_nome():
    g = _guardados()
    assert lg.nome_clicavel("Achados <BR> & Cia", "-1001111", g) == \
        '<a href="https://t.me/achados_br">Achados &lt;BR&gt; &amp; Cia</a>'
    assert lg.nome_clicavel("Sem link & cia", "-4000000000", g) == "Sem link &amp; cia"


def _dialogo(chat_id, titulo, usuario=None, ultima=None):
    return SimpleNamespace(entity=SimpleNamespace(id=chat_id, title=titulo, username=usuario),
                           message=SimpleNamespace(id=ultima) if ultima else None)


def test_guarda_o_que_as_conversas_da_conta_dizem(monkeypatch):
    monkeypatch.setattr(lg, "_chat_id", lambda entidade: str(entidade.id))
    pessoa = SimpleNamespace(entity=SimpleNamespace(id=9, first_name="Fulano"), message=None)
    total = lg.guardar_dialogos([_dialogo("-1001111", "A", "achados_br", 50),
                                 _dialogo("-1002222", "B", None, 987), pessoa])
    assert total == 2
    assert lg.link("-1001111", lg.ler_todos()) == "https://t.me/achados_br"
    assert lg.link("-1002222", lg.ler_todos()) == "https://t.me/c/2222/987"
    # O grupo tirou o @; a última mensagem que não veio fica a que estava.
    lg.guardar_dialogos([_dialogo("-1001111", "A", None, None)])
    assert lg.ler_todos()["-1001111"] == {"usuario": None, "convite": None, "ultima_msg": 50}


def test_bot_guarda_o_arroba_e_o_convite_ao_validar_um_grupo():
    import utils

    class Bot:
        async def get_chat(self, var):
            if var == "-1005555":
                return SimpleNamespace(id=-1005555, title="Canal", type="channel", full_name=None,
                                       username="canal_publico", invite_link=None)
            raise RuntimeError("chat not found")

    ok, id_final, nome = rodar(utils.validar_e_formatar_alvo(Bot(), "-1005555"))
    assert ok and id_final == "-1005555" and nome == "Canal"
    assert lg.link("-1005555", lg.ler_todos()) == "https://t.me/canal_publico"


def test_convite_do_grupo_comum_so_onde_a_conta_e_admin():
    def chat(numero, criador):
        return Chat(id=numero, title="G", photo=ChatPhotoEmpty(), participants_count=3, date=None,
                    version=1, creator=criador)

    pedidos = []

    async def client(requisicao):
        pedidos.append(requisicao.chat_id)
        return SimpleNamespace(full_chat=SimpleNamespace(
            exported_invite=SimpleNamespace(link="https://t.me/+convite_teste")))

    dialogos = [SimpleNamespace(entity=chat(5232187113, True), message=None),
                SimpleNamespace(entity=chat(4000000000, False), message=None)]
    assert rodar(lg.guardar_convites(client, dialogos)) == 1
    assert pedidos == [5232187113]
    assert lg.link("-5232187113", lg.ler_todos()) == "https://t.me/+convite_teste"
    # Já guardado: não pede de novo.
    assert rodar(lg.guardar_convites(client, dialogos)) == 0 and pedidos == [5232187113]


def test_painel_mostra_o_nome_como_atalho(bm):
    bm.salvar_nome_grupo("-1001111", "Achados BR")
    lg.guardar("-1001111", "achados_br")
    lg._recentes["lido_em"] = 0.0           # a leitura dos últimos 30 s ainda não tinha o grupo
    assert bm.rotulo_alvo("-1001111:5") == \
        '<b><a href="https://t.me/achados_br/5">Achados BR</a></b> (<code>-1001111_5</code>)'
