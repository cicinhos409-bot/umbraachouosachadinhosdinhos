"""Faxina do Acervo Viral: vídeos com mais de 7 dias e com produto fora da Shopee saem do canal."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from conftest import rodar

AGORA = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)


class Video:
    def __init__(self, msg_id, dias, video=True):
        self.id = msg_id
        self.date = AGORA - timedelta(days=dias)
        self.video = object() if video else None
        self.raw_text = f"🔗 Link do Produto:\nhttps://s.shopee.com.br/v{msg_id}"
        self.entities = None


class Conta:
    """Cliente do Telethon falso: o canal, as permissões da conta e o que ela apagou."""

    def __init__(self, mensagens, admin=True, pode_apagar=True):
        self.mensagens = list(mensagens)
        self.admin, self.pode_apagar = admin, pode_apagar
        self.apagadas = []

    async def get_me(self):
        return SimpleNamespace(first_name="Espião", last_name=None, username="conta_espiao")

    async def get_entity(self, alvo):
        return "acervo"

    async def get_permissions(self, canal, quem):
        return SimpleNamespace(is_admin=self.admin, delete_messages=self.pode_apagar)

    async def iter_messages(self, canal):
        for mensagem in sorted(self.mensagens, key=lambda m: m.date, reverse=True):
            yield mensagem

    async def delete_messages(self, canal, ids):
        self.apagadas.extend(ids)
        self.mensagens = [m for m in self.mensagens if m.id not in ids]


@pytest.fixture
def fx(monkeypatch):
    """faxina_viral com o produto de cada vídeo = o id dele e a API respondendo pelo dicionário a_venda."""
    import faxina_viral
    faxina_viral.a_venda = {}

    async def produto(mensagem):
        return f"10/{mensagem.id}"

    async def consulta(loja, item):
        return faxina_viral.a_venda.get(int(item), True)

    monkeypatch.setattr(faxina_viral, "produto_do_video", produto)
    monkeypatch.setattr(faxina_viral.api_shopee, "produto_a_venda", consulta)
    monkeypatch.setattr(faxina_viral, "PAUSA_ENTRE_CONFERENCIAS_S", 0)
    return faxina_viral


def test_sem_permissao_de_apagar_nao_apaga_e_avisa(fx):
    conta = Conta([Video(1, 30)], pode_apagar=False)
    resumo = rodar(fx.rodada(conta, AGORA))
    assert conta.apagadas == [] and resumo["situacao"] == "sem_permissao"
    assert "@conta_espiao" in fx.linha_status() and "não é administradora" in fx.linha_status()
    assert "Apagar mensagens" in fx.problema_de_permissao()


def test_video_com_mais_de_7_dias_sai_e_o_resto_fica(fx):
    # Pedido do Rafael em 16/10: vídeo antigo no Acervo Viral só enche o canal.
    conta = Conta([Video(1, 8), Video(2, 30, video=False), Video(3, 2), Video(4, 0.5)])
    resumo = rodar(fx.rodada(conta, AGORA))
    assert conta.apagadas == [1]                       # o texto antigo e os vídeos novos ficam
    assert resumo["videos_no_canal"] == 2 and resumo["apagados_idade_dia"] == 1
    assert fx.videos_no_canal() == 2


def test_produto_fora_da_shopee_sai_so_na_segunda_conferencia(fx):
    conta = Conta([Video(5, 3)])
    fx.a_venda[5] = False
    rodar(fx.rodada(conta, AGORA))
    assert conta.apagadas == []                        # uma falta só pode ser a Shopee fora do ar
    rodar(fx.rodada(conta, AGORA + timedelta(hours=6)))
    assert conta.apagadas == []                        # ainda não passou 1 dia
    resumo = rodar(fx.rodada(conta, AGORA + timedelta(hours=25)))
    assert conta.apagadas == [5] and resumo["apagados_produto_dia"] == 1


def test_consulta_sem_resposta_nao_apaga_nem_esquece_a_falta(fx):
    conta = Conta([Video(5, 3)])
    fx.a_venda[5] = False
    rodar(fx.rodada(conta, AGORA))
    fx.a_venda[5] = None
    rodar(fx.rodada(conta, AGORA + timedelta(hours=25)))
    assert conta.apagadas == []
    fx.a_venda[5] = False
    rodar(fx.rodada(conta, AGORA + timedelta(hours=31)))
    assert conta.apagadas == [5]


def test_produto_que_voltou_zera_a_falta(fx):
    conta = Conta([Video(6, 1.5)])
    fx.a_venda[6] = False
    rodar(fx.rodada(conta, AGORA))
    fx.a_venda[6] = True
    rodar(fx.rodada(conta, AGORA + timedelta(hours=25)))
    fx.a_venda[6] = False
    rodar(fx.rodada(conta, AGORA + timedelta(hours=50)))
    assert conta.apagadas == []                        # falta nova: conta do zero
    rodar(fx.rodada(conta, AGORA + timedelta(hours=75)))
    assert conta.apagadas == [6]


def test_antigos_saem_aos_poucos(fx):
    conta = Conta([Video(i, 10 + i / 100) for i in range(1, 151)])
    resumo = rodar(fx.rodada(conta, AGORA))
    assert len(conta.apagadas) == fx.LIMITE_APAGAR_POR_RODADA == 100
    assert resumo["antigos_pendentes"] == 50 and "50 antigos na fila" in fx.linha_status()
    rodar(fx.rodada(conta, AGORA + timedelta(hours=6)))
    assert len(conta.apagadas) == 150 and conta.mensagens == []


def test_api_que_nao_acha_quase_nada_nao_apaga_ninguem(fx):
    # A Shopee "perder" a maioria dos produtos de uma vez é problema da API, não dos produtos.
    conta = Conta([Video(i, 3) for i in range(1, 13)])
    for i in range(1, 13):
        fx.a_venda[i] = False
    rodar(fx.rodada(conta, AGORA))
    resumo = rodar(fx.rodada(conta, AGORA + timedelta(hours=25)))
    assert conta.apagadas == [] and resumo["api_suspeita"]


def test_produto_vem_do_link_da_legenda(monkeypatch):
    import faxina_viral

    async def seguir(link):
        if link.endswith("v1"):
            return [link, "https://shopee.com.br/product/123/456?sp_atk=x"]
        if link.endswith("v3"):
            return [link]                                   # o link não abriu agora
        return [link, "https://sv.shopee.com.br/share-video/abc"]

    monkeypatch.setattr(faxina_viral.api_shopee, "seguir_link", seguir)
    assert rodar(faxina_viral.produto_do_video(Video(1, 1))) == "123/456"
    assert rodar(faxina_viral.produto_do_video(Video(2, 1))) == ""      # vídeo da Shopee Vídeo: só a idade
    assert rodar(faxina_viral.produto_do_video(Video(3, 1))) is None    # tenta de novo depois
    sem_link = SimpleNamespace(raw_text="sem link", entities=None)
    assert rodar(faxina_viral.produto_do_video(sem_link)) is None


def test_acervo_do_viral_conta_so_o_que_esta_no_canal(bm):
    hoje = datetime.now(bm.fuso_horario).strftime("%Y-%m-%d")
    bm.salvar_metrica(hoje, "posts_total_viral", 5000)
    assert bm.gerar_fato_prova("viral") == "5000 vídeos já disponíveis no acervo"   # faxina sem rodar
    bm.db.salvar_config("faxina_viral", {"situacao": "ok", "videos_no_canal": 280})
    assert bm.gerar_fato_prova("viral") == "280 vídeos já disponíveis no acervo"
    assert "Faxina do Acervo Viral" in bm.montar_status()
