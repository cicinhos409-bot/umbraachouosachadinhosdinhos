"""
As rotas do Espelhador de canais (origens -> destino e as regras de cada uma), no banco
(chave CHAVE da tabela configuracoes), no mesmo formato do arquivo espelhos_config.json
que elas substituem: {"rotas": [rotas]}.

Quem usa: o painel_espelhos (cria, edita e remove rotas), o motor_userbot (captura pelas
rotas, desliga o "Esvaziar agora" depois de reagendar e grava o que o auditor confere em
cada canal), o bot_mestre (relatórios), o utils (origens de todos os robôs) e o inventario.

Toda gravação passa por atualizar(), que lê e grava numa transação só. Com o arquivo, o
motor_userbot regravava as rotas inteiras que tinha lido minutos antes: a rota criada ou
editada no painel nesse meio tempo sumia. Agora o motor muda só o que é dele.
(DECISOES.md, Código e manutenção)
"""
import json
import logging
import os

import db
from utils import normalizar_origens_rotas

CHAVE = "espelhador_rotas"
ARQUIVO = "espelhos_config.json"

logger = logging.getLogger("Rotas_Espelhador")


def _garantir_tabela():
    """A tabela configuracoes, caso este robô grave antes de o bot_mestre criá-la."""
    with db.conexao() as con:
        con.execute("CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)")


def _ler_arquivo():
    """As rotas do arquivo antigo, ou None se não houver arquivo legível."""
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not isinstance(dados, dict):
        return None
    if not isinstance(dados.get("rotas"), list):
        dados["rotas"] = []
    return dados


def _no_banco(dados):
    return isinstance(dados, dict) and isinstance(dados.get("rotas"), list)


def ler():
    """
    As rotas ({"rotas": [...]}), com as origens no formato de texto. Até o motor_userbot
    passar o arquivo para o banco (ao ligar, depois do deploy), lê o arquivo. Sem nenhum
    dos dois, nenhuma rota.
    """
    dados = db.ler_config(CHAVE, {})
    if not _no_banco(dados):
        dados = _ler_arquivo() or {"rotas": []}
    normalizar_origens_rotas(dados)
    return dados


def atualizar(alterar):
    """
    Lê as rotas, chama alterar(dados) e grava, tudo numa transação só
    (db.atualizar_config). alterar muda dados no lugar e devolve o que quiser repassar a
    quem chamou. Se as rotas ainda não estão no banco, começa pelo arquivo, que então
    vira .bkp. Devolve o retorno de alterar, ou None se der erro.
    """
    veio_do_arquivo = []

    def _alterar(dados):
        if not _no_banco(dados):
            dados.clear()
            dados.update(_ler_arquivo() or {"rotas": []})
            veio_do_arquivo.append(os.path.exists(ARQUIVO))
        normalizar_origens_rotas(dados)
        return ("gravou", alterar(dados))

    try:
        _garantir_tabela()
    except Exception as e:
        logger.error(f"❌ [Espelhador] Sem acesso ao banco para gravar as rotas: {e}")
        return None
    retorno = db.atualizar_config(CHAVE, _alterar)
    if retorno is None:
        return None
    if any(veio_do_arquivo):
        _aposentar_arquivo()
    return retorno[1]


def salvar(dados):
    """
    Grava as rotas inteiras, como o painel as deixou. Serve a quem leu e grava em
    seguida, sem esperar nada no meio; quem passa tempo com as rotas na mão (o motor)
    grava pelo atualizar() só o que mudou. True se gravou.
    """
    def _trocar(atual):
        atual.clear()
        atual.update(dados)
        return True

    return atualizar(_trocar) is True


def _aposentar_arquivo(sufixo=".bkp"):
    try:
        os.replace(ARQUIVO, ARQUIVO + sufixo)
        logger.info(f"📦 [Espelhador] Rotas passadas do {ARQUIVO} para o banco ({ARQUIVO}{sufixo} guardado).")
    except OSError as e:
        logger.error(f"❌ [Espelhador] Rotas já no banco, mas o {ARQUIVO} não virou {sufixo}: {e}")


def passar_arquivo_para_o_banco():
    """
    Chamado pelo motor_userbot ao ligar, quando a versão anterior dele já parou. Passa o
    arquivo para o banco. Se as rotas já estão no banco (o painel gravou antes) e o arquivo
    reapareceu (gravado por uma versão velha durante o deploy), valem as do banco, que
    têm a última edição do Rafael, e o arquivo é aposentado.
    """
    if not os.path.exists(ARQUIVO):
        return
    _garantir_tabela()
    de_fora = _ler_arquivo()
    if de_fora is None:
        _aposentar_arquivo(".ilegivel.bkp")
        return

    def _passar(dados):
        if not _no_banco(dados):
            dados.clear()
            dados.update(de_fora)
        return True

    if db.atualizar_config(CHAVE, _passar):
        _aposentar_arquivo()
