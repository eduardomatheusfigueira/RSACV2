#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — O que pode ser triado a partir do resumo.

A triagem por título e resumo pressupõe que exista resumo. Boa parte dos
registros não tem: nas coletas deste projeto, cerca de **28% dos pendentes
chegam sem nenhum resumo** — repositórios institucionais e catálogos de teses
frequentemente não o publicam no metadado.

Pior: parte do que chega no campo `abstract` **não é resumo**. Os coletores
capturam o que estiver ali, e ali costuma estar o nome do orientador
("Orientação: Profa. Dra. ..."), a contagem de páginas ("106 f."), o nome da
instituição, ou literalmente ", .". Mandar isso para a assistência não produz
uma decisão ruim: produz uma decisão sobre nada, com a mesma aparência de
confiança de uma decisão real — e gasta cota do provedor para isso.

Daí este módulo existir e ser um só: o mesmo critério precisa valer na fila da
tela, na consulta do lote e no contador, senão os três discordam e o
pesquisador perde a conta dos seus registros.

**O que este módulo NÃO faz:** descartar estudo. Um registro sem resumo continua
no acervo e continua contando no fluxo PRISMA. Ele apenas não entra na fila da
triagem assistida — porque não há o que assistir — e ganha um lugar próprio,
onde o pesquisador decide o que fazer: buscar o resumo, julgar pelo título, ou
excluir com motivo declarado.
"""

from typing import Optional

from sqlalchemy import func, or_

#: Tamanho mínimo, em caracteres, para o conteúdo do campo passar por resumo.
#:
#: Medido no acervo real antes de escolher. Abaixo de 80 caracteres o que se
#: encontra é metadado desgarrado — orientador, instituição, número de folhas.
#: Entre 100 e 200 já aparecem resumos curtos porém legítimos ("We overview our
#: recent development and testing of the FIDO rover..."), e excluí-los seria pior
#: do que deixar passar algum lixo: o custo de um falso negativo aqui é um
#: estudo relevante que some da fila.
TAMANHO_MINIMO_DE_RESUMO = 80


def resumo_e_triavel(resumo: Optional[str]) -> bool:
    """O resumo tem substância suficiente para uma triagem assistida?"""
    return len((resumo or "").strip()) >= TAMANHO_MINIMO_DE_RESUMO


def filtro_com_resumo(modelo):
    """Condição SQL para registros com resumo utilizável.

    Recebe o modelo em vez de importá-lo para não criar dependência de camada:
    `domain` não deve conhecer `infrastructure`.
    """
    return func.length(func.trim(func.coalesce(modelo.abstract, ""))) >= TAMANHO_MINIMO_DE_RESUMO


def filtro_sem_resumo(modelo):
    """Condição SQL para registros que a triagem assistida não alcança."""
    return or_(
        modelo.abstract.is_(None),
        func.length(func.trim(func.coalesce(modelo.abstract, ""))) < TAMANHO_MINIMO_DE_RESUMO,
    )
