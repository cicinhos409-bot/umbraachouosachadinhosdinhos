"""rotas_espelhador: as rotas do Espelhador no banco, gravadas sem um robô apagar o que o outro gravou."""
import glob
import json
import os
from types import SimpleNamespace

import pytest

import db
import motor_userbot as mu
import rotas_espelhador as rotas
from conftest import rodar

PASTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _arquivo(dados):
    with open(rotas.ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f)


def _nomes():
    return [r["nome"] for r in rotas.ler()["rotas"]]


def test_sem_arquivo_nem_banco_nao_ha_rotas():
    assert rotas.ler() == {"rotas": []}


def test_le_o_arquivo_ate_o_motor_passar_para_o_banco():
    _arquivo({"rotas": [{"nome": "R", "origens": [{"id": "-1001", "nome": "Canal"}]}]})
    assert rotas.ler()["rotas"][0]["origens"] == ["-1001"]        # origem antiga vira texto
    rotas.passar_arquivo_para_o_banco()
    assert not os.path.exists(rotas.ARQUIVO) and os.path.exists(rotas.ARQUIVO + ".bkp")
    assert db.ler_config(rotas.CHAVE)["rotas"][0]["nome"] == "R"
    assert _nomes() == ["R"]


def test_painel_gravando_antes_da_passagem_leva_o_arquivo_junto():
    _arquivo({"rotas": [{"nome": "R"}]})
    dados = rotas.ler()
    dados["rotas"].append({"nome": "Nova"})
    assert rotas.salvar(dados) is True
    assert _nomes() == ["R", "Nova"] and os.path.exists(rotas.ARQUIVO + ".bkp")


def test_arquivo_gravado_por_versao_velha_no_deploy_nao_desfaz_o_banco():
    rotas.salvar({"rotas": [{"nome": "Do painel"}]})
    _arquivo({"rotas": [{"nome": "Velha"}]})
    rotas.passar_arquivo_para_o_banco()
    assert _nomes() == ["Do painel"] and not os.path.exists(rotas.ARQUIVO)


def test_esvaziar_agora_desliga_so_o_que_o_ciclo_atendeu():
    # O ciclo de disparo leu as rotas minutos antes. Nesse meio tempo o Rafael criou uma
    # rota e pediu "Esvaziar agora" em outra: nada disso pode sumir.
    rotas.salvar({"rotas": [{"nome": "A", "esvaziar_agora": True}, {"nome": "B"}]})
    lida_pelo_ciclo = rotas.ler()
    dados = rotas.ler()
    dados["rotas"][1]["esvaziar_agora"] = True
    dados["rotas"].append({"nome": "C"})
    rotas.salvar(dados)
    mu.desligar_esvaziar_agora({r["nome"] for r in lida_pelo_ciclo["rotas"] if r.get("esvaziar_agora")})
    agora = {r["nome"]: r.get("esvaziar_agora") for r in rotas.ler()["rotas"]}
    assert agora == {"A": False, "B": True, "C": None}


class _Parar(Exception):
    pass


def test_auditor_grava_so_o_que_conferiu(monkeypatch):
    # O auditor espera o Telegram canal por canal. Enquanto isso, o painel muda a janela
    # da rota A e cria a rota B: as duas mudanças ficam, e a conferência também.
    rotas.salvar({"rotas": [{"nome": "A", "origens": ["@canal_a"], "destino": "-1009", "inicio": 10}]})

    async def validar(_cliente, canal):
        if canal == "@canal_a":
            dados = rotas.ler()
            dados["rotas"][0]["inicio"] = 8
            dados["rotas"].append({"nome": "B", "origens": ["-1005"], "destino": "-1006"})
            rotas.salvar(dados)
            return SimpleNamespace(title="Canal A"), "-1001"
        return SimpleNamespace(title="Destino"), str(canal)

    async def parar(_segundos):
        raise _Parar

    monkeypatch.setattr(mu, "validar_e_obter_entidade", validar)
    monkeypatch.setattr(mu.asyncio, "sleep", parar)
    with pytest.raises(_Parar):
        rodar(mu.monitorar_status_espelhos())

    a, b = rotas.ler()["rotas"]
    assert a["inicio"] == 8 and b["nome"] == "B"
    assert a["origens"] == ["-1001"]                                   # ID corrigido
    assert a["status_canais"] == {"-1001": {"status": "ok", "nome": "Canal A"},
                                  "-1009": {"status": "ok", "nome": "Destino"}}
    assert "status_canais" not in b                                    # fica para a próxima volta


def test_auditor_nao_grava_conferencia_de_canal_que_o_painel_trocou(monkeypatch):
    rotas.salvar({"rotas": [{"nome": "A", "origens": ["@velho"], "destino": "-1009"}]})

    async def validar(_cliente, canal):
        if canal == "@velho":
            dados = rotas.ler()
            dados["rotas"][0]["origens"] = ["-1002"]
            rotas.salvar(dados)
        return SimpleNamespace(title="X"), "-1001" if canal == "@velho" else str(canal)

    async def parar(_segundos):
        raise _Parar

    monkeypatch.setattr(mu, "validar_e_obter_entidade", validar)
    monkeypatch.setattr(mu.asyncio, "sleep", parar)
    with pytest.raises(_Parar):
        rodar(mu.monitorar_status_espelhos())
    assert rotas.ler()["rotas"][0]["origens"] == ["-1002"]


def test_ninguem_le_ou_grava_o_arquivo_das_rotas():
    # Com o arquivo, o motor regravava as rotas que leu minutos antes por cima do que o
    # painel gravou nesse meio tempo. Tudo passa pelo rotas_espelhador.
    culpados = []
    for caminho in glob.glob(os.path.join(PASTA, "*.py")):
        if os.path.basename(caminho) == "rotas_espelhador.py":
            continue
        if "espelhos_config.json" in open(caminho, encoding="utf-8").read():
            culpados.append(os.path.basename(caminho))
    assert culpados == [], "use o rotas_espelhador: " + ", ".join(culpados)
