# 🧪 26 — Testes, Verificação e Linha de Base Numérica

> **RSAC V2 — Revisão Sistemática Assistida por Computador**  
> **Data:** Agosto de 2026  
> **Status:** Vigente e Normativo  
> **Objetivo:** Estabelecer a baseline numérica de partida e as 4 camadas de verificação contínua para prevenir regressões e degradação na UI.

---

## 1. Linha de Base Numérica (Baseline de Partida)

As métricas abaixo representam o estado inicial auditado em agosto de 2026 e servem como teto máximo a ser reduzido a zero ao longo das fases:

| Indicador Numérico | Baseline de Partida (Hoje) | Meta Final (Fase 7) |
|---|---|---|
| Ocorrências de fontes literais (9–11px fora de tokens) | **168** | **0** (todos usando tokens) |
| Cores hexadecimais literais fora do sistema de tema | **143** | **0** (100% tokens CSS) |
| Chamadas ao método `clickDomByText` / `clickDomByIndex` | **34** | **0** (100% store/handlers diretos) |
| Classes ad-hoc de botões concorrentes | **25** | **0** (todos usando `<Button />`) |
| Variações ad-hoc de empty states | **11** | **0** (todos usando `<EmptyState />`) |
| Elementos interativos sem `aria-label` / `:focus-visible` | **99%** | **0%** (100% em conformidade AA) |
| Ocupação vertical de moldura no Protocol Studio | **42%** | **< 25%** da altura da janela |

---

## 2. As 4 Camadas de Verificação de Qualidade

```
┌─────────────────────────────────────────────────────────────┐
│ Camada 4: Testes E2E de Fluxo & Regressão Visual            │
├─────────────────────────────────────────────────────────────┤
│ Camada 3: Testes de Integração de Ações & Store             │
├─────────────────────────────────────────────────────────────┤
│ Camada 2: Testes Unitários de Componentes (Vitest)          │
├─────────────────────────────────────────────────────────────┤
│ Camada 1: Verificação Estática (TypeScript + ESLint + CSS)  │
└─────────────────────────────────────────────────────────────┘
```

### Camada 1: Verificação Estática & Linters
- **TypeScript**: `npm run build` ou `npx tsc --noEmit` para garantir ausência de erros de tipo.
- **ESLint**: Garantir que novos componentes respeitem regras de hooks e tipagem estrita.

### Camada 2: Testes Unitários de Componentes (`Vitest`)
- Testes de renderização dos componentes canônicos (`Button`, `Badge`, `Dialog`, `Tooltip`, `EmptyState`).
- Verificação de variantes, tamanhos, estados desabilitados e propagação de eventos `onClick`.

### Camada 3: Testes de Integração de Ações & Ribbon
- Testes que comprovam que o acionamento de um botão no Ribbon executa a ação esperada no store ou na página ativa sem disparar eventos sintéticos no DOM.

### Camada 4: Testes E2E de Jornada e Acessibilidade
- Validação do fluxo completo: Criação de Projeto → Protocolo → Coleta → Deduplicação → Triagem 1 → Extração PDF → Relatórios.
- Auditoria automatizada de acessibilidade via axe-core / Playwright para verificação de contraste e conformidade ARIA.

---

## 3. Portões de Aceite por Fase (Quality Gates)

Nenhuma fase é dada como concluída sem que:
1. `npx tsc --noEmit` passe com 0 erros.
2. `npm run test` passe 100% das asserções.
3. Não haja aumento nas métricas da baseline (regressão proibida).
4. O app execute em ambiente local sem warnings críticos no console de desenvolvimento.
