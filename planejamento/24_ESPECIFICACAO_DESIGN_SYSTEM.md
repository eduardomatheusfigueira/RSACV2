# 📐 24 — Especificação Normativa do Design System

> **RSAC V2 — Revisão Sistemática Assistida por Computador**  
> **Data:** Agosto de 2026  
> **Status:** Vigente e Normativo  
> **Princípio Fundamental:** O sistema descreve o produto que existe e estabelece governança formal sobre ele.

---

## 1. Tokens de Tipografia e Escala Compacta

A escala tipográfica é atualizada para acolher oficialmente a alta densidade de informação requerida pela plataforma de pesquisa acadêmica:

| Token CSS | Tamanho | Line Height | Uso Recomendado |
|---|---|---|---|
| `--font-size-3xs` | `9px` (0.5625rem) | 1.2 | Badges mínimos, contadores subscritos, rodapés de metadados |
| `--font-size-2xs` | `10px` (0.625rem) | 1.25 | Rótulos do Ribbon, tags secundárias, carimbos de tempo |
| `--font-size-xs-alt` | `11px` (0.6875rem) | 1.3 | Células de tabela densa, textos de ajuda secundários |
| `--font-size-xs` | `12px` (0.75rem) | 1.4 | Textos auxiliares, inputs compactos, descrições de itens |
| `--font-size-sm` | `13px` (0.8125rem) | 1.45 | Corpo secundário, botões padrão, itens de lista |
| `--font-size-base` | `14px` (0.875rem) | 1.5 | Corpo padrão de leitura, inputs de formulário |
| `--font-size-md` | `15px` (0.9375rem) | 1.5 | Cabeçalhos de cards, subtítulos de seção |
| `--font-size-lg` | `16px` (1rem) | 1.4 | Títulos de cards de destaque, botões principais |
| `--font-size-xl` | `18px` (1.125rem) | 1.3 | Títulos de seção do estúdio |
| `--font-size-2xl` | `22px` (1.375rem) | 1.2 | Títulos principais de páginas |

---

## 2. Grade e Sistema de Espaçamento

O sistema de espaçamento adota as micro-frações necessárias para interfaces desktop de alta precisão:

- `--spacing-3xs`: `2px` (micro-ajustes de ícones e bordas)
- `--spacing-2xs`: `4px` (gaps internos de badges e tags)
- `--spacing-xs-alt`: `6px` (padding interno de botões compactos)
- `--spacing-xs`: `8px` (espaçamento base entre campos e botões)
- `--spacing-sm`: `12px` (padding interno de cards compactos)
- `--spacing-md`: `16px` (padding padrão de cards e grids)
- `--spacing-lg`: `24px` (separação de seções)
- `--spacing-xl`: `32px` (margens externas de páginas)

---

## 3. Catálogo de Componentes Canônicos

Para eliminar a fragmentação de classes CSS, todos os elementos de interface devem convergir para os seguintes componentes canônicos em `frontend/src/components/ui/`:

### 3.1. Primitivos de Interação & Feedback
1. **`<Button />`**:
   - Variantes: `primary`, `secondary`, `outline`, `ghost`, `danger`, `decision-include`, `decision-exclude`, `decision-pending`.
   - Tamanhos: `compact` (24px), `sm` (28px), `md` (34px), `large` (42px).
2. **`<Badge />` / `<StatusPill />`**:
   - Status: `success`, `warning`, `danger`, `info`, `neutral`, `ai`.
3. **`<Tooltip />`** (Baseado em `@radix-ui/react-tooltip`):
   - Delay de 300ms, suporte a atalhos de teclado visíveis.
4. **`<Dialog />` / `<Modal />`** (Baseado em `@radix-ui/react-dialog`):
   - Foco retido, fechamento via Escape e clique externo, overlay escurecido com transição suave.
5. **`<EmptyState />`**:
   - Composição padronizada: Ícone contextual, Título claro, Descrição sucinta, Ação primária opcional.

---

## 4. Contratos de Acessibilidade (WCAG 2.1 Nível AA)

1. **Navegabilidade por Teclado**: Todo elemento interativo deve ter anel de foco visível padronizado:
   ```css
   :focus-visible {
     outline: 2px solid var(--color-brand-primary, #606c38);
     outline-offset: 2px;
   }
   ```
2. **Rótulos ARIA**: Todo botão que contenha apenas ícone DEVE obrigatoriamente possuir `aria-label` descritivo.
3. **Contraste de Cor**: Relação de contraste mínima de 4.5:1 para texto normal e 3.0:1 para elementos de controle sobre fundos temáticos.
