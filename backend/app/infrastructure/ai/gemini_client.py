#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Revsist — Google Gemini AI Client.
Integração com a API Google Gemini (via v1beta REST)
com suporte a rotação de API keys, modelos configurados no Revsist e output JSON estruturado.
"""

import asyncio
import json
import time
import logging
import re
from typing import Dict, List, Optional

import httpx

from app.domain.entities import Paper, Protocol
from app.infrastructure.ai.base import (
    DiagnosticoDeConexao,
    ProvedorIndisponivel,
    BaseAIClient,
    ProtocolSuggestions,
    ScreeningResult,
    validar_resposta_de_triagem,
)
from app.infrastructure.ai.prompts import (
    build_field_assist_prompt,
    build_protocol_suggestion_prompt,
    build_screening_prompt,
)

logger = logging.getLogger(__name__)


class GeminiAIClient(BaseAIClient):
    """Cliente para Google Gemini com rotação de chaves e JSON mode."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    FALLBACK_MODELS = (
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-flash-lite-latest",
    )

    def __init__(
        self,
        api_keys: List[str],
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.2,
    ):
        super().__init__(provider_name="gemini", model_name=model_name or "gemini-2.5-flash")
        self.api_keys = [k.strip() for k in api_keys if k.strip()]
        self.current_key_idx = 0
        self.temperature = temperature
        # Assinatura do conjunto de chaves: separa o rodízio de um usuário do de
        # outro sem precisar carregar identidade até aqui.
        self._assinatura = "|".join(sorted(k[-8:] for k in self.api_keys))

    def _get_current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("Nenhuma API Key do Gemini configurada.")
        return self.api_keys[self.current_key_idx % len(self.api_keys)]

    @staticmethod
    def _marca(modelo: str, chave: str) -> str:
        """Identidade do par cota — é o que o Google limita, não a chave só."""
        return f"{modelo}|{chave}"

    def _pares_disponiveis(self, chaves: List[str], modelos: List[str]) -> List[tuple]:
        """Pares (modelo, chave) livres, na ordem do rodízio.

        A ordem é o ponto. Antes, o cliente esgotava o modelo preferido em
        TODAS as chaves antes de olhar o seguinte — o que fazia o custo por
        estudo crescer ao longo do lote: os primeiros passavam de primeira, e os
        últimos precisavam percorrer uma lista cada vez mais cheia de pares em
        descanso antes de achar um livre. Medido num lote de dez: os oito
        primeiros em segundos, o nono em 40s, o décimo em 70s.

        Girando sobre os pares, a carga se espalha desde o começo entre todos os
        modelos e todas as chaves. O orçamento total é o mesmo; o que muda é
        que ele é gasto por igual, em vez de esgotar uma fonte de cada vez — e
        o fim do lote deixa de ser mais caro que o começo.
        """
        agora = time.monotonic()
        pares = [
            (m, k)
            for m in modelos
            for k in chaves
            if self._DESCANSO_POR_CHAVE.get(self._marca(m, k), 0.0) <= agora
        ]
        if not pares:
            return []
        # Ordem: todas as chaves do modelo preferido, depois as do seguinte.
        # Combinada com o deslocamento que avança a cada sucesso, isso faz
        # chamadas consecutivas caírem em CHAVES diferentes — que é o recurso
        # mais escasso, por serem projetos distintos — antes de passar ao
        # próximo modelo.
        pares.sort(key=lambda par: (modelos.index(par[0]), chaves.index(par[1])))
        inicio = self._POSICAO_DO_RODIZIO.get(self._assinatura, 0) % len(pares)
        return pares[inicio:] + pares[:inicio]

    def _proximo_descanso(self, chaves: List[str], modelos: List[str]) -> float:
        """Quanto falta para o primeiro par chave+modelo voltar a ficar livre."""
        agora = time.monotonic()
        prazos = [
            self._DESCANSO_POR_CHAVE.get(self._marca(m, k), 0.0) - agora
            for m in modelos
            for k in chaves
            if self._DESCANSO_POR_CHAVE.get(self._marca(m, k), 0.0) > agora
        ]
        return max(0.0, min(prazos)) if prazos else 0.0

    def _rotate_key(self) -> None:
        if self.api_keys:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
            logger.info(f"[Gemini] Chave rotacionada para índice {self.current_key_idx}")

    def _clean_json(self, raw_text: str) -> str:
        """Extrai JSON limpo mesmo se a IA incluir markdown backticks ou retornar um array."""
        text = raw_text.strip()
        if "```json" in text:
            match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()
        elif "```" in text:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        # Localizar início de objeto '{' ou de array '['
        first_brace = text.find("{")
        first_bracket = text.find("[")

        if first_bracket != -1 and (first_brace == -1 or first_bracket < first_brace):
            last_bracket = text.rfind("]")
            if last_bracket != -1 and last_bracket > first_bracket:
                return text[first_bracket : last_bracket + 1].strip()
        elif first_brace != -1:
            last_brace = text.rfind("}")
            if last_brace != -1 and last_brace > first_brace:
                return text[first_brace : last_brace + 1].strip()

        return text

    # Quantas rodadas de espera antes de desistir de um estudo. Quatro cobre
    # com folga a janela de um minuto do limite de taxa, que é o caso comum, e
    # ainda desiste rápido o bastante para não travar o lote quando o problema
    # é de verdade.
    # Duas rodadas, e não quatro. Com o descanso das chaves preservado entre
    # chamadas, insistir aqui só duplica a espera que o acelerador do lote já
    # faz — e foi essa soma que transformou um artigo em cinco minutos.
    TENTATIVAS_APOS_LIMITE = 2

    # Quanto tempo uma chave recusada por limite fica de fora do rodízio quando
    # o provedor não diz por quanto esperar. A janela do limite do Gemini é de
    # um minuto; 30s é metade dela — o bastante para não insistir na chave
    # queimada, pouco o bastante para ela voltar ao conjunto no mesmo lote.
    DESCANSO_MINIMO_DA_CHAVE = 30.0

    # ── Memória das chaves, compartilhada entre instâncias ─────────────
    #
    # Estes dois dicionários são de CLASSE, e é o ponto todo. A fábrica constrói
    # um cliente novo a cada artigo triado; guardar aqui dentro da instância
    # significava jogar fora, a cada estudo, tudo o que se havia aprendido: a
    # posição do rodízio voltava à primeira chave — justamente a que costuma
    # estar esgotada — e o descanso das recusadas era esquecido.
    #
    # O efeito era medível: cada artigo redescobria do zero quais chaves estavam
    # sem cota, gastando dezenas de recusas e minutos de espera para chegar de
    # novo à mesma conclusão. Um lote de três estudos levava mais de cinco
    # minutos no primeiro deles.
    #
    # O que se sabe sobre uma chave é propriedade da chave, não de quem a usa.
    # A chave da memória é o par CHAVE + MODELO, e isso é essencial: o Google
    # limita por `GenerateRequestsPerDayPerProjectPerModel`, ou seja, cada
    # modelo tem a sua própria cota dentro do mesmo projeto. Guardar o descanso
    # só por chave fazia o esgotamento de um modelo bloquear todos os outros —
    # e a cadeia de reserva, que existe justamente para essa hora, nunca era
    # alcançada. Foi o que deixou a triagem em lote parada com oito chaves que
    # respondiam normalmente em `gemini-2.5-flash`.
    _DESCANSO_POR_CHAVE: Dict[str, float] = {}
    _POSICAO_DO_RODIZIO: Dict[str, int] = {}

    async def _call_gemini_api(self, prompt: str) -> dict:
        """
        Percorre chave e modelo antes de esperar, porque o Gemini limita por
        **projeto E por modelo** — o identificador da cota é literalmente
        `GenerateRequestsPerDayPerProjectPerModel`.

        O que isso implica, e foi tudo medido contra a API real:

        1. **Trocar de CHAVE ajuda.** Cada chave do AI Studio pertence a um
           projeto, e cada projeto tem cota própria. Quem cadastra oito chaves
           tem oito orçamentos — desde que se use todos. Uma versão anterior
           parava na primeira recusa e ia dormir, com sete chaves boas ociosas.

        2. **Trocar de MODELO ajuda, e às vezes é a única saída.** Com a cota
           diária de `gemini-3.6-flash` esgotada nas oito chaves, as mesmas oito
           respondiam HTTP 200 em `gemini-2.5-flash`. Uma versão anterior marcava
           a chave inteira como em descanso, o que bloqueava todos os modelos de
           uma vez e nunca alcançava a cadeia de reserva — deixando a triagem
           parada com cota disponível ao lado.

        3. **Esperar só ajuda se o limite for por minuto.** A cota diária não
           volta hoje; insistir nela é gastar requisição. Por isso o par
           chave+modelo esgotado por dia sai do rodízio por horas, enquanto os
           outros seguem em uso.
        """
        if not self.api_keys:
            raise ValueError("Nenhuma API Key do Google Gemini cadastrada nas Configurações.")

        # Priorizar chaves válidas de formato Google AI Studio (iniciadas em AIzaSy)
        valid_keys = [k for k in self.api_keys if k.startswith("AIzaSy")]
        keys_to_try = valid_keys if valid_keys else self.api_keys

        models_to_try = [self.model_name] + [m for m in self.FALLBACK_MODELS if m != self.model_name]

        ultimo_erro = "sem resposta dos modelos configurados"

        for rodada in range(1, self.TENTATIVAS_APOS_LIMITE + 1):
            espera_pedida = 0.0
            pares_esgotados = 0
            # Pares que nem existem — modelo fora de catálogo. Saem do
            # denominador: um modelo inexistente não é evidência sobre a cota,
            # e contá-lo apagava o diagnóstico verdadeiro.
            pares_indisponiveis = 0
            houve_cota_diaria = False
            pares_totais = len(models_to_try) * len(keys_to_try)

            pares = self._pares_disponiveis(keys_to_try, models_to_try)
            pares_esgotados = pares_totais - len(pares)

            if pares:
                for model, key in pares:
                    resultado, estado, detalhe = await self._tentar_uma_vez(model, key, prompt)

                    if estado == "ok":
                        # Rodízio: a próxima chamada começa no par SEGUINTE, e
                        # não neste. Fixar no que deu certo concentra a carga
                        # justamente onde o limite está mais perto de estourar.
                        self._POSICAO_DO_RODIZIO[self._assinatura] = (
                            self._POSICAO_DO_RODIZIO.get(self._assinatura, 0) + 1
                        )
                        return resultado

                    if estado == "limite":
                        # Outra chave é outro projeto, e portanto outro limite:
                        # seguir para a próxima é mais barato que esperar.
                        pares_esgotados += 1
                        espera, e_diaria = detalhe if isinstance(detalhe, tuple) else (detalhe, False)
                        espera = espera or 0.0
                        houve_cota_diaria = houve_cota_diaria or e_diaria
                        if not e_diaria:
                            espera_pedida = max(espera_pedida, espera)
                        self._DESCANSO_POR_CHAVE[self._marca(model, key)] = (
                            time.monotonic()
                            + (
                                self.DESCANSO_DE_COTA_DIARIA
                                if e_diaria
                                else max(self.DESCANSO_MINIMO_DA_CHAVE, espera)
                            )
                        )
                        continue

                    # Falha que não é cota. Também sai do rodízio por um tempo:
                    # insistir no mesmo par a cada artigo do lote é o que
                    # transformava um modelo fora do ar em oito requisições
                    # perdidas por estudo.
                    modelo_sumiu = isinstance(detalhe, str) and "indisponível" in detalhe
                    if modelo_sumiu:
                        pares_indisponiveis += 1
                    self._DESCANSO_POR_CHAVE[self._marca(model, key)] = time.monotonic() + (
                        self.DESCANSO_DE_MODELO_INEXISTENTE if modelo_sumiu else self.DESCANSO_APOS_FALHA
                    )
                    ultimo_erro = detalhe or ultimo_erro

            pares_uteis = max(1, pares_totais - pares_indisponiveis)

            if pares_esgotados < pares_uteis:
                # Sobrou falha que não é limite: esperar não muda nada.
                break

            if rodada == self.TENTATIVAS_APOS_LIMITE:
                break

            if houve_cota_diaria:
                # Cota diária não volta hoje: esperar segundos é perder tempo.
                break

            # Basta UM par voltar para a chamada seguir. Esperar o maior prazo
            # pedido — que era o que se fazia — deixa o lote parado enquanto um
            # par já livre está à disposição, e o prazo de um par nada diz sobre
            # o dos outros: são projetos e modelos independentes.
            espera = (
                self._proximo_descanso(keys_to_try, models_to_try)
                or espera_pedida
                or min(60.0, 5.0 * (2 ** (rodada - 1)))
            )
            logger.warning(
                f"[Gemini] Todos os {pares_uteis} pares chave+modelo no limite de taxa "
                f"(rodada {rodada}/{self.TENTATIVAS_APOS_LIMITE}). Aguardando {espera:.0f}s..."
            )
            await asyncio.sleep(espera)

        if pares_esgotados >= pares_uteis:
            if houve_cota_diaria:
                raise ProvedorIndisponivel(
                    "A cota DIÁRIA do plano gratuito do Gemini acabou em todas as combinações "
                    f"de chave e modelo ({pares_uteis}). Ela reinicia à meia-noite do Pacífico; "
                    "até lá, só um modelo ainda não usado ou um plano pago destravam a triagem.",
                    esgotado_por_cota=True,
                )
            raise ProvedorIndisponivel(
                f"Todas as {len(keys_to_try)} chave(s) do Gemini estão no limite de taxa, mesmo "
                f"depois de {self.TENTATIVAS_APOS_LIMITE} esperas. Reduza o ritmo da triagem "
                "em lote ou aguarde a renovação da cota.",
                esgotado_por_cota=True,
            )

        raise ProvedorIndisponivel(
            f"Não foi possível obter resposta válida dos modelos Gemini configurados: {ultimo_erro}"
        )

    async def _tentar_uma_vez(self, model: str, key: str, prompt: str):
        """
        Uma requisição.

        Devolve `(dado, estado, detalhe)`, com `estado` em:
        `ok` (dado preenchido), `limite` (429, e `detalhe` é a espera em
        segundos pedida pelo provedor) ou `falha` (`detalhe` é a descrição).
        """
        url = f"{self.BASE_URL}/{model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(url, json=payload)

                if res.status_code == 200:
                    data = res.json()
                    candidate_text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    cleaned = self._clean_json(candidate_text)
                    return json.loads(cleaned), "ok", None

                if res.status_code == 429:
                    return None, "limite", self._analisar_429(res)

                if res.status_code in (400, 404):
                    logger.warning(
                        f"[Gemini] Modelo '{model}' retornou {res.status_code}. Tentando o próximo..."
                    )
                    return None, "falha", f"modelo '{model}' indisponível (HTTP {res.status_code})"

                logger.warning(f"[Gemini] Erro na API (HTTP {res.status_code}): {res.text[:100]}")
                return None, "falha", f"HTTP {res.status_code}"

        except json.JSONDecodeError as e:
            logger.error(f"[Gemini] Falha ao decodificar JSON gerado: {e}")
            raise RuntimeError("O modelo Gemini não retornou um JSON válido.")
        except Exception as e:
            logger.warning(f"[Gemini] Falha na requisição ({type(e).__name__}): {e}")
            return None, "falha", f"{type(e).__name__}: {e}"

    #: Quanto uma dupla chave+modelo fica de fora quando a cota é DIÁRIA.
    #:
    #: A cota diária do plano gratuito reinicia à meia-noite do Pacífico. Não há
    #: espera de segundos que a recupere, e insistir só gasta requisição —
    #: então o par sai do rodízio por um tempo longo, enquanto os outros modelos,
    #: que têm cota própria, continuam sendo usados normalmente.
    DESCANSO_DE_COTA_DIARIA = 6 * 3600.0

    #: Descanso de um par que falhou por motivo transitório — 503, tempo
    #: esgotado, erro de rede.
    #:
    #: Sem isto, um modelo momentaneamente fora do ar era retentado em TODAS as
    #: chaves a cada artigo do lote: `gemini-flash-latest` devolvendo 503
    #: custava oito requisições por estudo antes de o rodízio chegar ao modelo
    #: que respondia. Dois minutos bastam para não repetir o erro no mesmo lote
    #: e ainda voltar a testar o modelo se ele se recuperar.
    DESCANSO_APOS_FALHA = 120.0

    #: Descanso de um par cujo modelo não existe mais no catálogo. Não adianta
    #: reavaliar em minutos: só um novo catálogo mudaria a resposta.
    DESCANSO_DE_MODELO_INEXISTENTE = 6 * 3600.0

    @classmethod
    def _analisar_429(cls, res) -> tuple:
        """Devolve `(espera_em_segundos, e_cota_diaria)`.

        A distinção importa muito: um limite POR MINUTO passa sozinho em
        instantes, e esperar é a resposta certa. Um limite POR DIA não passa
        hoje — esperar é só perder tempo, e o caminho é trocar de modelo.
        O Google diz qual é qual no `quotaId` da resposta.
        """
        diaria = False
        try:
            for detalhe in res.json().get("error", {}).get("details", []):
                if not str(detalhe.get("@type", "")).endswith("QuotaFailure"):
                    continue
                for violacao in detalhe.get("violations", []):
                    if "perday" in str(violacao.get("quotaId", "")).lower():
                        diaria = True
        except Exception:  # noqa: BLE001
            pass
        return cls._espera_do_429(res), diaria

    @staticmethod
    def _espera_do_429(res) -> float:
        """
        Quanto esperar depois de um 429, segundo o próprio provedor.

        O Gemini informa o atraso de duas formas, e usa mais a segunda: o
        cabeçalho `Retry-After` e, no corpo, um `RetryInfo` com `retryDelay`
        do tipo "31s". Ler só o cabeçalho — como se fazia — deixava passar
        justamente o caso comum.
        """
        cabecalho = res.headers.get("retry-after") if hasattr(res, "headers") else None
        if cabecalho:
            try:
                return min(60.0, max(1.0, float(cabecalho)))
            except (TypeError, ValueError):
                pass

        try:
            for detalhe in res.json().get("error", {}).get("details", []):
                atraso = detalhe.get("retryDelay")
                if atraso:
                    return min(60.0, max(1.0, float(str(atraso).rstrip("s"))))
        except Exception:
            pass

        return 0.0
    async def analyze_screening(
        self,
        paper: Paper,
        protocol: Protocol,
    ) -> ScreeningResult:
        prompt = build_screening_prompt(paper, protocol)
        data = await self._call_gemini_api(prompt)

        # Validação contra o contrato, com o desvio registrado em vez de
        # coagido em silêncio (doc 29 §29.9.2).
        decisao, confianca, justificativa, valida, nota = validar_resposta_de_triagem(data)
        if not valida:
            logger.warning(
                "[%s] Resposta de triagem fora do contrato (%s) — decisão rebaixada para Pendente.",
                self.provider_name, nota,
            )

        inc = data.get("criterios_inclusao_atendidos") or data.get("criterios_inclusao") or {}
        exc = data.get("criterios_exclusao_atendidos") or data.get("criterios_exclusao") or {}
        if not isinstance(inc, dict):
            inc = {}
        if not isinstance(exc, dict):
            exc = {}

        return ScreeningResult(
            decision=decisao,
            inclusion_criteria=inc,
            exclusion_criteria=exc,
            justification=justificativa,
            confidence=confianca,
            model_used=self.model_name,
            provider="gemini",
            response_valid=valida,
            validation_note=nota,
        )

    async def generate_protocol_suggestions(
        self,
        title: str,
        methodology: str,
        initial_description: str = "",
    ) -> ProtocolSuggestions:
        return await self.suggest_protocol(title, methodology, initial_description)

    async def suggest_protocol(
        self,
        title: str,
        methodology: str,
        description: Optional[str] = None,
    ) -> ProtocolSuggestions:
        prompt = build_protocol_suggestion_prompt(title, methodology, description)
        data = await self._call_gemini_api(prompt)

        desc_pt = data.get("descritores_pt", [])
        desc_en = data.get("descritores_en", [])
        desc_es = data.get("descritores_es", [])

        # Respeitar estritamente a regra de no máximo 5 pares por idioma
        return ProtocolSuggestions(
            objective=data.get("objetivo", ""),
            pico_population=data.get("pico_populacao", ""),
            pico_intervention=data.get("pico_intervencao", ""),
            pico_comparison=data.get("pico_comparacao", ""),
            pico_outcome=data.get("pico_desfecho", ""),
            descriptors_pt=desc_pt[:5],
            descriptors_en=desc_en[:5],
            descriptors_es=desc_es[:5],
            inclusion_criteria=data.get("criterios_inclusao", []),
            exclusion_criteria=data.get("criterios_exclusao", []),
            extraction_questions=data.get("perguntas_extracao", []),
        )

    async def assist_field(
        self,
        field_label: str,
        field_guidelines: str = "",
        current_value: str = "",
        project_title: str = "",
        methodology: str = "PRISMA-ScR",
        project_context: Optional[dict] = None,
        action: str = "generate",
        custom_instruction: str = "",
        field_id: str = "",
    ) -> dict:
        prompt = build_field_assist_prompt(
            field_label=field_label,
            field_guidelines=field_guidelines,
            current_value=current_value,
            project_title=project_title,
            methodology=methodology,
            project_context=project_context,
            action=action,
            custom_instruction=custom_instruction,
            field_id=field_id,
        )
        data = await self._call_gemini_api(prompt)
        return {
            "suggested_text": data.get("suggested_text", ""),
            "explanation": data.get("explanation", ""),
            "model_used": self.model_name,
            "provider": self.provider_name,
        }

    async def test_connection(self) -> bool:
        """Testa conectividade e validade das chaves com o Google Gemini."""
        return (await self.diagnosticar_conexao()).ok

    async def diagnosticar_conexao(self) -> DiagnosticoDeConexao:
        """
        Confere cada chave cadastrada e diz o que encontrou.

        Três correções sobre o teste anterior, e todas vieram de casos reais:

        1. **Testa todas as chaves**, e não só a primeira. Quem cadastra oito
           chaves faz isso justamente porque uma pode falhar; reprovar o
           conjunto por causa da primeira leva o pesquisador a trocar chaves
           que estavam boas.
        2. **Não gasta cota de geração.** `generateContent` consumia uma
           requisição do limite por minuto só para dizer "está ligado" — e,
           repetido, era ele próprio quem provocava o 429 seguinte. A consulta
           ao catálogo (`GET /models/...`) valida a chave e a existência do
           modelo sem gerar nada.
        3. **Separa limite de taxa de chave inválida.** Eram a mesma mensagem,
           e a frase escolhida ("verifique a API Key") acusava justamente o que
           não tinha problema.
        """
        entradas = [k for k in self.api_keys if k]
        chaves = [k for k in entradas if k.startswith("AIzaSy")]
        ignoradas = len(entradas) - len(chaves)

        if not entradas:
            return DiagnosticoDeConexao(
                ok=False,
                mensagem="Nenhuma API Key do Google Gemini cadastrada nas Configurações.",
                provedor=self.provider_name,
                modelo=self.model_name,
            )

        if not chaves:
            return DiagnosticoDeConexao(
                ok=False,
                mensagem=(
                    f"Nenhuma das {len(entradas)} entradas cadastradas tem formato de chave do "
                    "Google AI Studio (elas começam com 'AIzaSy'). Gere a chave em "
                    "aistudio.google.com/apikey."
                ),
                provedor=self.provider_name,
                modelo=self.model_name,
                chaves_ignoradas=ignoradas,
            )

        boas, recusadas, limitadas = 0, 0, 0
        ultimo_detalhe = ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            for chave in chaves:
                try:
                    res = await client.get(f"{self.BASE_URL}/{self.model_name}?key={chave}")
                except Exception as e:  # noqa: BLE001
                    recusadas += 1
                    ultimo_detalhe = f"{type(e).__name__}: {e}"
                    continue

                if res.status_code == 200:
                    boas += 1
                elif res.status_code == 429:
                    limitadas += 1
                else:
                    recusadas += 1
                    try:
                        ultimo_detalhe = str(res.json().get("error", {}).get("message", ""))[:160]
                    except Exception:  # noqa: BLE001
                        ultimo_detalhe = f"HTTP {res.status_code}"

        base = DiagnosticoDeConexao(
            ok=False,
            mensagem="",
            provedor=self.provider_name,
            modelo=self.model_name,
            chaves_testadas=len(chaves),
            chaves_boas=boas,
            chaves_recusadas=recusadas,
            chaves_ignoradas=ignoradas,
            limite_de_taxa=limitadas > 0,
        )

        sobra = (
            f" ({ignoradas} entrada(s) sem formato de chave do AI Studio foram ignoradas.)"
            if ignoradas
            else ""
        )

        if boas:
            base.ok = True
            recusa = f" {recusadas} recusada(s)." if recusadas else ""
            espera = f" {limitadas} sob limite de taxa no momento." if limitadas else ""
            base.mensagem = (
                f"Conexão estabelecida: {boas} de {len(chaves)} chave(s) responderam."
                f"{recusa}{espera}{sobra}"
            )
            return base

        if limitadas and not recusadas:
            base.mensagem = (
                "As chaves estão válidas, mas o Gemini está recusando por limite de taxa "
                "neste momento. Aguarde um minuto e teste de novo — não é preciso trocar "
                f"as chaves.{sobra}"
            )
            return base

        detalhe = f" Último erro: {ultimo_detalhe}" if ultimo_detalhe else ""
        base.mensagem = (
            f"Nenhuma das {len(chaves)} chave(s) foi aceita para o modelo "
            f"'{self.model_name}'.{detalhe}{sobra}"
        )
        return base
