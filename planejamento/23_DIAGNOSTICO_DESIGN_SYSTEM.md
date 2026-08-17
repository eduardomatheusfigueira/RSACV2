# 🔍 23 — Diagnóstico da UI e Design System

> **RSAC V2 — Revisão Sistemática Assistida por Computador**  
> **Data:** Agosto de 2026  
> **Status:** Vigente e Normativo  
> **Tese Central:** Interface **competente e de identidade distintiva**, porém **mal governada** no código.

---

## 1. Sumário Executivo do Diagnóstico

A auditoria quantitativa e qualitativa da interface do RSAC V2 revelou que a aplicação possui um visual maduro, profissional e com forte identidade temática (paleta *Black Forest / Field Oak* e modos alternativos elegantes). No entanto, **o design system foi declarado de forma idealizada e nunca implementado como componentes React com contratos estritos**.

Como consequência, as páginas resolveram suas necessidades reais criando regras CSS ad-hoc, quebrando a governança e gerando pontos críticos de manutenção.

---

## 2. Métricas Reais Auditadas no Código

| Indicador Auditado | Medição Real | Limiar do Sistema Anterior | Diagnóstico Técnico |
|---|---|---|---|
| **Fontes Compactas (9px, 10px, 11px)** | **168 ocorrências** | Mínimo era `--font-size-xs: 12px` | A escala tipográfica ignorava a densidade real do app. |
| **Cores Literais (Hardcoded HEX/RGBA)** | **143 ocorrências** | 0 (Deveriam usar tokens CSS) | Cores fixas espalhadas em arquivos `.css` individuais. |
| **Ocupação Vertical de Moldura (Protocol Studio)** | **42% da altura útil** | Máx. recomendado: 20–25% | Sobram apenas 2 campos visíveis sem scroll no viewport padrão. |
| **Classes de Botão Concorrentes** | **25 classes distintas** | 1 componente `<Button />` | Inconsistência de alturas, paddings, raio e estados de foco. |
| **Classes de Estado Vazio (Empty States)** | **11 variações ad-hoc** | 1 componente `<EmptyState />` | Duplicação de ícones, títulos e botões de ação. |
| **Acessibilidade (ARIA & Foco)** | **1 `aria-label` / 1 `:focus-visible`** | WCAG 2.1 Nível AA | Baixa navegabilidade por teclado e leitores de tela. |
| **Acoplamento Ribbon ↔ DOM** | **34 chamadas `clickDomByText`** | 0 (Deveriam ser funções diretas) | Ribbon simula clique no DOM buscando texto em português. |

---

## 3. Principais Patologias Identificadas

### 3.1. Escala Tipográfica Desconectada da Realidade
A densidade de dados do RSAC V2 exige textos compactos para metadados de artigos, badges de status, tabelas comparativas e atalhos de barra de ferramentas. O design system antigo partia de `12px` como menor degrau, forçando os desenvolvedores a usar `11px`, `10px` e `9px` hardcoded 168 vezes.

### 3.2. Moldura Vertical Excessiva no Estúdio de Protocolo
No Estúdio de Protocolo, a combinação de:
- Barra de Título / Janela Electron
- Ribbon Bar de 3 fileiras
- Breadcrumbs / Abas de Etapas
- Cabeçalho do Card de Seção
consome **42% da altura da janela de 1080p**, comprimindo o editor de texto real e prejudicando o fluxo de redação contínua do pesquisador.

### 3.3. Fragilidade do Mecanismo de Disparo do Ribbon
O `TopRibbonBar.tsx` utiliza funções auxiliares como:
```typescript
const clickDomByText = (selector: string, text: string) => {
  const elements = Array.from(document.querySelectorAll(selector))
  const target = elements.find(el => el.textContent?.trim().includes(text))
  if (target) (target as HTMLElement).click()
}
```
Isso faz com que o botão "Salvar Tudo" do Ribbon procure um botão com texto "Salvar Tudo" na página ativa. Se o texto for renomeado para "Salvar Alterações" ou internacionalizado, o botão do Ribbon falha silenciosamente.

### 3.4. Incongruência de Diretrizes Metodológicas
Mesmo com o projeto configurado para diretrizes ambientais ou sociais como **CEE/ROSES** (27 itens) ou **Campbell**, o corpo da interface mantinha textos hardcoded como `"Conforme PRISMA-ScR Item 1"` e `"Checklist (22 Itens)"`, gerando confusão metodológica.

---

## 4. Conclusão e Diretriz de Ação

A solução **não é uma reescrita visual (big-bang)**, mas sim uma **re-ancoragem normativa**:
1. O Design System deve passar a descrever os tamanhos e densidades reais do produto.
2. Criar a camada canônica de componentes React utilizando a base já instalada (`@radix-ui/*`, `lucide-react`, `sonner`).
3. Refatorar o acoplamento do Ribbon para comunicação tipada e direta.
