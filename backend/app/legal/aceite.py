#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Aviso e Termos do BETA, versionados (doc 38 L-12; doc 43 §43.10).

Este módulo é a **fonte única** do texto que a pessoa marca como lido. Ele fica
no código, e não no banco nem num CMS, por três razões:

1. **Versionamento real.** O que a pessoa aceitou em março tem de continuar
   recuperável em dezembro. Aqui isso é o histórico do git, de graça.
2. **Prova.** `UserModel.terms_version` guarda a versão aceita. Sem o texto
   correspondente versionado ao lado, esse campo registra um número que não se
   sabe traduzir.
3. **Revisão.** Mudança em texto legal passa por diff, como código.

Sobre o que este documento **não** faz
======================================
Ele não recolhe consentimento para o envio de dados ao provedor de IA. Isso é
tratamento com transferência internacional, exige consentimento **específico**
(art. 33, VIII), e o art. 8º §4º diz que autorização genérica é nula — juntar as
duas coisas num só "aceito" invalidaria justamente a que mais precisa valer. O
consentimento da IA é pedido no momento do uso, por projeto (Fase 3.12).
"""

from __future__ import annotations

import hashlib

# ── Versão ────────────────────────────────────────────────────────────
#
# Formato `AAAA-MM-N`. Só muda quando o **conteúdo** muda de forma que altere
# o que a pessoa concordou — correção de vírgula não é versão nova. Ao mudar,
# quem já aceitou volta a ver a tela, porque a comparação é por igualdade.
VERSAO = "2026-08-1"

# ── Lacunas a preencher antes de publicar ─────────────────────────────
#
# Estes marcadores são de propósito. Preenchê-los com dado plausível produziria
# um documento jurídico com informação falsa, publicado sob o seu nome — e o
# aviso de privacidade é declaração vinculante, não texto de vitrine.
#
# `verificar_lacunas()` recusa a partida do perfil `server` enquanto sobrarem.
MARCADORES = ("[NOME COMPLETO]", "[E-MAIL DE CONTATO]", "[CIDADE/ESTADO]")


TITULO = "Aviso e Termos do Revsist BETA"

ROTULO_DA_CAIXA = (
    "Li o aviso acima e estou ciente de que o Revsist está em BETA, "
    "roda num computador pessoal e pode ficar indisponível ou perder "
    "até 24 horas de trabalho."
)

TEXTO = """
# Aviso e Termos do Revsist BETA

**Versão 2026-08-1.** Leia antes de continuar. Este texto explica o que o
Revsist faz com os seus dados e em que condições ele funciona hoje. Ele é
curto de propósito: um aviso que ninguém lê não informa ninguém.

## 1. O que é, e em que fase está

O Revsist é uma ferramenta para conduzir revisões sistemáticas e de escopo:
coleta de referências, triagem contra critérios, extração e exportação.

Está em **BETA** e sendo distribuído a um grupo pequeno de pessoas convidadas.
Não é um produto acabado. Você vai encontrar defeitos, e é esperado que
encontre.

## 2. Onde os seus dados ficam — o ponto mais importante deste aviso

Nesta fase o Revsist roda **no computador pessoal de [NOME COMPLETO]**, em
[CIDADE/ESTADO], no Brasil, ligado à internet por conexão doméstica. **Não é
um servidor profissional em datacenter.** Na prática:

- **O serviço pode sair do ar sem aviso** — queda de energia, queda de
  internet, reinício do sistema. Não há garantia de disponibilidade nem
  compromisso de prazo para voltar.
- **Existe backup diário, mas uma falha pode custar até 24 horas de
  trabalho.** Se a sua revisão tem prazo apertado, exporte seu material com
  frequência: a exportação está sempre disponível na tela de Exportação.
- **O disco é cifrado** e o banco de dados não é acessível pela rede.
- **Os dados ficam no Brasil**, exceto o que você mesmo enviar a um provedor
  de IA (ver o item 6).

Se essas condições não servem para o seu trabalho, **não crie conta.** Não há
problema nenhum em recusar — o convite existe justamente para você poder
decidir com essa informação.

## 3. Que dados são tratados

**Sobre você**

- Nome e e-mail, vindos da sua conta Google quando você entra por ela.
- Registro de acesso: data, hora e endereço IP, guardados por 90 dias e usados
  para conter tentativa de acesso indevido.
- As chaves de API de provedores de IA que você configurar, guardadas
  cifradas. Elas nunca são exibidas de volta e ninguém além de você as usa.

**Sobre a sua pesquisa**

- Projetos, protocolos e critérios que você escrever.
- Referências coletadas nas bases e as suas decisões de triagem, com a data e
  a justificativa.
- Os PDFs que você anexar.

**O Revsist não pede nem trata dado pessoal sensível** — origem racial, convicção
religiosa, opinião política, dado de saúde, biométrico ou genético (art. 5º, II,
da LGPD). Ver o item 10.

## 4. Para quê

Os dados sobre você servem para autenticar seu acesso, separar o seu material
do de outras pessoas e responder a você quando pedir suporte. Os dados da sua
pesquisa servem para prestar o serviço — eles são o serviço.

**Nada é usado para publicidade, vendido, cedido ou compartilhado com
terceiros.** Não há rastreamento de comportamento, cookie de terceiro nem
ferramenta de análise de audiência.

## 5. Quem tem acesso

**[NOME COMPLETO]**, responsável pelo serviço, tem acesso técnico ao servidor
e, portanto, ao banco de dados. Ele não lê o conteúdo da sua pesquisa por
hábito, mas **pode ver o que for necessário para resolver um problema que você
relatar**. Sendo um serviço operado por uma pessoa só, essa é a situação real,
e você tem direito de sabê-la.

Ninguém mais tem acesso.

## 6. Inteligência artificial — e o que não está sendo pedido aqui

O Revsist pode sugerir pareceres de triagem usando um provedor de IA. Isso é
**opcional** e depende de você configurar uma chave própria.

Quando você usa esse recurso, o **título e o resumo** da publicação analisada
são enviados ao provedor que você escolher, que pode estar fora do Brasil.
Nomes de autores **não** são enviados. Nada sobre você — nome, e-mail, conta —
é enviado junto.

Esse envio **não está sendo autorizado por este aviso.** Ele é transferência
internacional de dados e exige consentimento específico, que será pedido a você
no momento em que ativar o recurso, projeto por projeto, com o destino
nomeado. Você pode usar o Revsist inteiro sem nunca acionar IA.

O parecer da IA é **sugestão para a sua conferência**, nunca decisão. A
responsabilidade metodológica pela revisão é sua.

## 7. Por quanto tempo os dados ficam

- **Sua conta e sua pesquisa:** enquanto você quiser. Se você pedir a
  eliminação, a conta é desativada e apagada em 7 dias — prazo que existe para
  você poder desistir.
- **Registros de acesso:** 90 dias.
- **Registro das operações de tratamento:** 5 anos, sem o conteúdo tratado —
  guarda que houve tratamento, nunca o que foi tratado. É o que a lei exige
  para prestação de contas.
- **Backups:** ciclo de 30 dias. Um dado apagado pode persistir em backup até
  o ciclo se completar.
- **Se o BETA for encerrado:** ver o item 11.

## 8. Seus direitos

A LGPD (art. 18) garante a você, a qualquer momento e sem custo:

- saber que dados existem sobre você e obter cópia deles;
- corrigir o que estiver errado;
- pedir a eliminação da sua conta e de tudo que é seu;
- saber com quem os dados foram compartilhados (no Revsist: com o provedor de
  IA que você mesmo escolher, e com mais ninguém);
- revogar consentimento que tenha dado;
- se opor a um tratamento, ou reclamar à Autoridade Nacional de Proteção de
  Dados (ANPD).

**Como exercer:** pelas telas do próprio Revsist, ou escrevendo para
[E-MAIL DE CONTATO]. A resposta vem em até 15 dias.

## 9. Segurança

Sua senha nunca é guardada — só um resumo criptográfico dela. As chaves de IA
são guardadas cifradas. A sessão usa cookie que scripts da página não
conseguem ler. O acesso é por HTTPS. O disco do servidor é cifrado.

Nada disso torna um sistema invulnerável, e um serviço nesta fase e nestas
condições tem risco maior do que um serviço maduro em datacenter. **Se houver
incidente de segurança que possa te afetar, você será avisado** — e a ANPD
também, como a lei manda.

## 10. O que você não deve colocar aqui

Por ser um serviço em BETA num computador pessoal, **não** use o Revsist para:

- dados de saúde identificáveis de pacientes, ou qualquer dado pessoal
  sensível (art. 5º, II);
- dados de crianças e adolescentes;
- material sob sigilo contratual, judicial ou de comitê de ética que exija
  ambiente controlado.

Metadados bibliográficos públicos, protocolos e as suas próprias anotações de
pesquisa são o uso previsto.

## 11. Se o BETA for encerrado

Você será avisado com **pelo menos 30 dias** de antecedência, e nesse período
poderá exportar tudo. Passado o prazo, os dados são eliminados. O Revsist não
guarda material de quem saiu.

## 12. Mudanças neste texto

Se este aviso mudar de forma que altere o que você concordou, a nova versão
será apresentada e a sua concordância pedida de novo. Versões anteriores ficam
registradas.

## Contato

**[NOME COMPLETO]** — [E-MAIL DE CONTATO]

Controlador dos dados, nos termos do art. 5º, VI, da LGPD.
""".strip()


def sha256() -> str:
    """
    Resumo do texto exato desta versão.

    Guardar o resumo junto do aceite responde à pergunta que uma fiscalização
    faz: *o que exatamente essa pessoa leu?* A versão sozinha depende de
    alguém ter lembrado de incrementá-la ao editar; o resumo não depende de
    ninguém.
    """
    return hashlib.sha256(TEXTO.encode("utf-8")).hexdigest()


def verificar_lacunas() -> list[str]:
    """Marcadores ainda não preenchidos. Vazio = pronto para publicar."""
    return [m for m in MARCADORES if m in TEXTO]
