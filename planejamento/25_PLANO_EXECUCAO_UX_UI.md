# 25 — Plano de Execução — UX e UI

> Como sair do estado medido no doc 23 e chegar ao alvo do doc 24, sem parar o
> desenvolvimento de funcionalidade e sem um "grande redesenho" que trava o
> produto por meses.

---

## 25.0 Situação em 17/08/2026

O plano começou a ser executado no mesmo dia em que foi escrito, e fora da
ordem prevista — o que se mostrou acertado: as fases de maior valor saíram
primeiro.

| Fase | Situação | Evidência |
|---|:---:|---|
| **1 — Tokens** | ✅ **concluída** | **Zero** literal de cor, tipografia, espaçamento, raio e `z-index` em todo o `src/`. `lint:tokens --strict` passa com as 5 categorias fechadas |
| **2 — Componentes** | 🟡 parcial | `components/ui/` entregue com Radix (`Dialog`, `Tooltip`), `Button`, `Badge`, `Card`, `FormControls`. **Ainda não adotado por nenhuma página** — as 25 classes de botão antigas seguem em uso |
| **3 — Proporção e comando** | 🟡 parcial | Moldura do Protocolo de 42% → **29%**; `<PageHeader>` aplicado e comando duplicado removido dessa tela. Falta aplicar às outras 7 e adotar `<Button>`/`<Card>`/`<EmptyState>` |
| **4 — Registro de comandos** | ✅ **concluída** | `useRibbonStore` nas 7 páginas; acionamento por DOM de 34 → **0**; botões refletem estado real |
| **5 — Acessibilidade** | 🟡 parcial | `:focus-visible` global (era 1 regra no app inteiro); abas do Estúdio com `role="tab"`/`aria-selected`; confirmação de salvamento e carregamento com `aria-live`. Faltam os 15 `onClick` em `div`, os 5 modais e a auditoria com `axe` |
| **6 — Conteúdo por diretriz** | 🟡 parcial | Ajuda e rótulos do Estúdio vêm do catálogo via `fieldKey`; contagem do checklist correta; os rótulos do diagrama deixaram de citar PRISMA 2020 fixo. Restam 5 modelos de texto inseríveis que citam a diretriz na própria prosa |
| **7 — Higiene** | 🟡 parcial | Sidebar removida (−372 linhas). Faltam as dependências não importadas e a decomposição dos arquivos grandes |

**Lição registrada.** A Fase 1 foi executada redefinindo os valores dos tokens
em vez de migrar os pontos de uso. Como não havia referência visual, ~192
elementos mudaram de forma e o texto encolheu em cascata sem que ninguém
percebesse — inclusive o campo de escrita do manuscrito, que caiu para 11 px.
Foi exatamente o risco de probabilidade **Alta** previsto em § 25.11, e a
mitigação prevista (referência visual **antes** de começar) não foi aplicada.
A referência de 104 imagens já existe agora; a partir daqui ela é obrigatória —
e provou o valor na mesma sessão: pegou as etiquetas de base acadêmica
ilegíveis em `platinum-dusk`, que tinham recebido token de chrome numa
superfície de conteúdo. Nenhuma leitura de código mostraria isso.

---

## 25.1 Estratégia

**Ordem obrigatória, por dependência real:** cada fase existe porque a
seguinte não pode ser feita sem ela.

```
Fase 1 ─ Tokens que descrevem o produto              ← nada compõe sem vocabulário
   │
Fase 2 ─ Biblioteca de componentes                   ← nada se padroniza sem peça
   │
   ├── Fase 3 ─ Proporção e hierarquia de comando    ← precisa de PageHeader/Toolbar
   │
   └── Fase 4 ─ Registro de comandos                 ← mata o acionamento por DOM
          │
          ├── Fase 5 ─ Acessibilidade e teclado      ← precisa do comando tipado
          │
          └── Fase 6 ─ Conteúdo por diretriz
                 │
              Fase 7 ─ Higiene e refino estético
```

**Três compromissos que governam a execução:**

1. **Nada de big bang.** Cada fase entrega um aplicativo funcionando. A
   migração é por página, com o padrão antigo convivendo com o novo até a
   última página migrar.
2. **A regra entra junto com o código que a cumpre.** O verificador de tokens
   (doc 26) começa como aviso e só vira erro quando a última violação daquela
   categoria some. Regra que quebra o build sem caminho de saída é regra que
   vai ser desligada.
3. **Referência visual antes de migrar.** As capturas das 8 telas nas 13
   paletas são tiradas **antes** da Fase 1 e comparadas a cada fase. Mudança
   visual não intencional é regressão, e sem a referência ela passa
   despercebida.

**Esforço estimado**: ~6 a 8 semanas em dedicação parcial. As Fases 1, 2 e 4
concentram o valor — se o trabalho for interrompido, é depois delas que deve
parar.

---

## 25.2 Decisões que precisam do autor antes da Fase 1

| # | Decisão | Recomendação | Por quê |
|:-:|---|---|---|
| **D1** | Ribbon **ou** sidebar como navegação | **Ribbon.** Aposentar `Sidebar.tsx` e `Sidebar.css` | 372 linhas de código morto que ainda recebem manutenção (doc 23 § 23.9). Manter os dois duplica todo trabalho de layout |
| **D2** | Adotar Radix | **Sim**, para `Dialog`, `Tabs`, `Tooltip`, `Select`; remover `DropdownMenu` e `Separator` se não usados | Instalados desde o início, nunca importados; resolvem prontos o § 23.7. Escrever à mão custa semanas e sai pior |
| **D3** | Renomear `--text-base` (15 px) para `--text-md` | **Sim**, com codemod na Fase 1 | Faz o 11 px virar o padrão nomeado que já é na prática. Redefinir em silêncio quebraria a leitura longa |
| **D4** | Densidade configurável (compacta / confortável) | **Não agora.** Fixar a densidade compacta atual | Dobra a matriz de validação (13 paletas × 2 densidades). Reavaliar após a Fase 7 |
| **D5** | Suporte a leitor de tela como requisito de release | **Sim** | O app é acadêmico e institucional; acessibilidade tende a ser exigida em compra pública |

---

## 25.3 Fase 1 — Tokens que descrevem o produto ✅ CONCLUÍDA

**Objetivo**: `globals.css` passa a descrever a interface que existe, e o
verificador passa a apontar quem foge dela.

| # | Tarefa | Entregável |
|:-:|---|---|
| 1.1 | Reescrever a escala tipográfica conforme doc 24 § 24.3 | 9 degraus, com o 11 px nomeado `--text-sm` |
| 1.2 | Codemod dos 184 `font-size` literais → token | Zero literal fora de `globals.css` |
| 1.3 | Acrescentar `--space-px`, `--space-0-5`, `--space-1-5` | Grade cobre 1, 2, 4, 6 px |
| 1.4 | Codemod dos 309 espaçamentos literais → token | `5px` e `3px` arredondados ao vizinho |
| 1.5 | Criar tokens de chrome, fonte acadêmica e overlay (§ 24.5) | ~12 tokens novos × 13 paletas |
| 1.6 | Substituir as 143 cores literais pelos tokens novos | Zero cor fora de `globals.css` |
| 1.7 | Criar a escala nomeada de `z-index` (§ 24.6) | 8 tokens; os 8 valores ad hoc migrados |
| 1.8 | Consolidar raio e elevação em 4 valores cada | Sem `50%` fora de pontos de estado |
| 1.9 | Escrever `scripts/lint-design-tokens.mjs` | Roda em modo aviso; imprime violações por arquivo |

**Critérios de aceite**

- `lint-design-tokens` reporta **0 violações** de cor, tipografia, espaçamento,
  raio e `z-index`.
- Comparação visual das 8 telas × 13 paletas contra a referência: nenhuma
  diferença não intencional.
- As etiquetas de base acadêmica no ribbon mudam de cor junto com o tema.

> ⚠️ **Risco**: os codemods tocam ~640 declarações. Fazer um commit por
> categoria (tipografia, espaçamento, cor, raio, z-index), cada um com a
> comparação visual anexada. Um commit único é irrevisável.

---

## 25.4 Fase 2 — Biblioteca de componentes 🟡 (entregue, não adotada)

**Objetivo**: existir a peça antes de exigir que as telas a usem.

| # | Tarefa | Entregável |
|:-:|---|---|
| 2.1 | `<Button>` e `<IconButton>` com 5 estados e 3 tamanhos | Substituem as 25 classes de botão |
| 2.2 | `<Tag>` com 6 tons | Substitui `db-badge`, `tab-pill`, `*-badge` |
| 2.3 | `<Field>`, `<TextInput>`, `<TextArea>`, `<Select>` | `label`/`htmlFor` e `aria-describedby` embutidos |
| 2.4 | `<Card>` e `<Panel>` | Substituem `neo-card` e contêineres de coluna |
| 2.5 | `<PageHeader>` | Fonte única da altura de 44 px |
| 2.6 | `<EmptyState>` e `<StatusView>` | Substituem as 11 classes de vazio |
| 2.7 | `<Modal>` sobre `@radix-ui/react-dialog` | Foco preso, `Escape`, foco devolvido |
| 2.8 | `<Tabs>` sobre `@radix-ui/react-tabs` | `role="tab"`, `aria-selected`, setas |
| 2.9 | `<Tooltip>` sobre `@radix-ui/react-tooltip` | Substitui `title=` nativo |
| 2.10 | `<Metric>` e `<Toolbar>`/`<ToolbarGroup>` | Contadores e grupos do ribbon |
| 2.11 | Página interna `/dev/componentes` com todos os estados | Galeria viva para conferência visual |

**Critérios de aceite**

- A galeria mostra cada componente nos 5 estados, nas 13 paletas.
- Navegação por teclado percorre a galeria inteira com foco sempre visível.
- Nenhuma tela migrada ainda — a fase entrega a biblioteca, não a adoção.

> A galeria em `/dev/componentes` é o que torna a Fase 3 barata: sem ela, cada
> divergência só aparece quando já está espalhada por seis telas.

---

## 25.5 Fase 3 — Proporção e hierarquia de comando 🟡 (cabeçalho e estados fechados)

**Objetivo**: devolver a tela ao conteúdo e acabar com o comando duplicado.

| # | Tarefa | Entregável |
|:-:|---|---|
| 3.1 ✅ | Aplicar `<PageHeader>` nas 8 páginas | 44 px em todas (47 no Protocolo, por causa do seletor de diretriz) |
| 3.2 ✅ | Aplicar a hierarquia do § 24.9: cabeçalho fica só com a ação primária | 1 ação por tela, medida. Os comandos que saíram já viviam no ribbon; a auditoria de duplicatas ganhou lugar na aba Triagem |
| 3.3 | Mover os filtros de triagem do ribbon para a lista | Fim dos filtros em duplicata na mesma tela |
| 3.4 | Comprimir o toolstrip do ribbon para ≤ 96 px | Estado de recolhimento lembrado entre sessões |
| 3.5 | Reduzir as abas do estúdio de 114 px para uma faixa única | Grupos "a priori"/"a posteriori" por cor, não por caixa |
| 3.6 | Redesenhar o Estúdio de Protocolo para leitura contínua | Alvo: 6+ campos visíveis a 1440 × 900 |
| 3.7 🟡 | Aplicar `<Card>`, `<Panel>`, `<EmptyState>` nas 8 páginas | `<EmptyState>`/`<LoadingState>` adotados nas 6 telas que os desenhavam à mão; `<Card>` e `<Panel>` seguem pendentes |
| 3.8 | Levar a composição de duas colunas da Coleta para Extração e Exportação | Referência interna, não invenção |

**Critérios de aceite**

- Moldura ≤ **25%** da altura em **todas** as 8 telas a 1440 × 900 (hoje o
  Protocolo está em 42%).
- Nenhuma ação aparece duas vezes na mesma tela.
- Estúdio de Protocolo com pelo menos 6 campos visíveis sem rolagem.
- Comparação visual: as mudanças são as pretendidas, tela a tela.

---

## 25.6 Fase 4 — Registro de comandos ✅

**Objetivo**: eliminar os 34 acionamentos por DOM — o achado 🔴 A1.

| # | Tarefa | Entregável |
|:-:|---|---|
| 4.1 | Definir `CommandId`, `Command` e o store do registro | Contrato tipado do § 24.9 |
| 4.2 | `useRegisterCommands()` para as páginas declararem o que executam | Registro no montar, baixa no desmontar |
| 4.3 | Migrar Protocolo: 3 comandos + 6 seções | `clickDomByText`/`ByIndex` some da aba |
| 4.4 | Migrar Triagem: decisões, assistência, acervo | Botões refletem o estado real da lista |
| 4.5 | Migrar Coleta, Extração, Exportação, Configurações | 34 pontos zerados |
| 4.6 | Ribbon passa a ler o registro | Comando ausente ou indisponível aparece desabilitado |
| 4.7 | Remover `clickDom`, `clickDomByText`, `clickDomByIndex` | Regra R-3 vira erro no verificador |
| 4.8 | Atalhos declarados no comando e exibidos no tooltip | Atalhos deixam de ser folclore |

**Critérios de aceite**

- Zero `document.querySelector` para acionar interface.
- Renomear qualquer rótulo de botão não desliga nada — teste de regressão que
  troca um rótulo e confere que o comando continua funcionando.
- Nenhum botão do ribbon habilitado sem alvo executável.
- Todo atalho existente aparece no tooltip do comando correspondente.

---

## 25.7 Fase 5 — Acessibilidade e teclado 🟡 (controles, modais e contraste fechados)

**Objetivo**: cumprir os 10 critérios do § 24.10. A Fase 4 é pré-requisito —
sem comando tipado não há o que anunciar.

| # | Tarefa | Entregável |
|:-:|---|---|
| 5.1 ✅ | `:focus-visible` global, verificado nas 13 paletas | A-2 |
| 5.2 ✅ | Converter os 15 `onClick` em `<div>`/`<span>` para `<button>` | 14 convertidos (`<button>` ou `<label>`); o cartão de projeto ficou `<div>` com papel e teclado, por conter o botão de excluir |
| 5.3 | Migrar as 2 UIs de aba para `<Tabs>` | A-5 |
| 5.4 ✅ | Migrar os 5 modais para `<Modal>` | 6 migrados para o `<Dialog>` do Radix (havia um sexto, o relatório de deduplicação). Variante `window` preserva a janela clássica |
| 5.5 🟡 | `aria-live` em progresso de coleta, lote de triagem e confirmações | Confirmações e carregamentos anunciados; erros passam por `sonner`. Progresso de coleta e lote seguem pendentes |
| 5.6 | Revisar a ordem de tabulação contra a ordem visual nas 8 telas | A-3 |
| 5.7 🟡 | `aria-label` em todo botão só de ícone | Os que o axe-core acusa estão fechados; falta varredura manual dos que têm apenas `title` |
| 5.8 | `<Field>` em todos os formulários | A-8 |
| 5.9 | Ícone junto da cor nas decisões de triagem | A-10 |
| 5.10 ✅ | Auditoria automatizada com `axe-core` nas 8 telas | Rodada nas 8 telas × 13 paletas, não só na paleta padrão |
| 5.11 | Percurso completo por teclado, das 8 telas | Roteiro do doc 26 |

**Critérios de aceite**

- `axe-core` sem violação crítica ou séria nas 8 telas.
- Fluxo completo — criar projeto → protocolo → coleta → triagem → extração →
  exportar — executável **só com teclado**.
- Contraste conforme § 24.5 nas 13 paletas.

---

## 25.8 Fase 6 — Conteúdo dependente da diretriz 🟡 (rótulos feitos, modelos pendentes)

**Objetivo**: o achado A8 — o app exibir numeração do PRISMA-ScR sob CEE/ROSES
é erro de conteúdo metodológico, não detalhe cosmético.

| # | Tarefa | Entregável |
|:-:|---|---|
| 6.1 | Levantar todo texto de diretriz fixo no JSX | Inventário dos pontos |
| 6.2 | Estender o catálogo com a ajuda por seção e por campo | Campo novo em `ProtocolDefinition` |
| 6.3 | Substituir "Conforme PRISMA-ScR Item n" pelo texto do catálogo | Corpo do formulário correto |
| 6.4 | Corrigir "checklist PRISMA-ScR (22 itens)" no ribbon | Nome e contagem da diretriz ativa |
| 6.5 | Tornar o diagrama de fluxo consciente da diretriz | Rótulo e etapas conforme a metodologia |
| 6.6 | Cobrir os rótulos "ITEM n — ESSENCIAL" | Vêm do catálogo |

**Critérios de aceite**

- Com cada uma das 11 metodologias ativas, nenhuma tela cita outra diretriz.
- Verificador acusa `PRISMA` literal em JSX fora do catálogo (regra R-7).

---

## 25.9 Fase 7 — Higiene e refino estético 🟡 (Sidebar removida)

**Objetivo**: pagar o peso morto e fazer a passada final de acabamento.

| # | Tarefa | Entregável |
|:-:|---|---|
| 7.1 | Remover `Sidebar.tsx` e `Sidebar.css` (decisão D1) | −372 linhas |
| 7.2 | Remover dependências não importadas que sobrarem | `package.json` honesto |
| 7.3 | Corrigir README: stack anunciada = stack usada | Sem Radix/Recharts fantasmas |
| 7.4 | Decompor `ProtocolPage.tsx` (2.979 linhas) em seções | Nenhum arquivo > ~400 linhas |
| 7.5 | Idem para Triagem, Configurações e Extração | Regra R-5 |
| 7.6 | Tokens de movimento e `prefers-reduced-motion` global | § 24.8 |
| 7.7 | Esqueletos de carregamento no lugar dos spinners centrais | § 24.9 |
| 7.8 ✅ | Toasts com `sonner` para sucesso fora da vista | Conclusão de coleta e de triagem em lote; erros de domínio do log store |
| 7.9 ✅ | Gráficos reais no dashboard (pendência doc 12 § 4.9) | **Decidido: remover `recharts`.** Ver nota abaixo |
| 7.10 | Passada de acabamento: alinhamento óptico, ritmo, alinhamento de ícones | Julgamento visual, tela a tela |

> **Nota sobre 7.9 — por que não há gráfico.** A pendência do doc 12 § 4.9
> pressupunha que faltavam gráficos. Ao abrir o Painel, o que faltava era
> outra coisa: três dos quatro números mostravam `—` porque ninguém tinha
> ligado `/projects/:id/stats`, que o backend já servia. Ligados, mostram o
> acervo do projeto ativo — a pergunta que o Painel responde é "onde está a
> minha revisão", não "quantos artigos há no disco"; somar todos os projetos
> exigiria uma requisição por projeto para responder pergunta que ninguém faz.
>
> Com os números no lugar, `recharts` não tem o que desenhar. Quatro
> contadores escalares não viram gráfico, e a única visualização real do
> aplicativo — o fluxograma PRISMA — tem forma prescrita pela diretriz e já é
> desenhada à mão na Exportação, com boa razão: uma biblioteca genérica de
> gráficos brigaria com o formato exigido em vez de ajudar. Dependência
> removida.

**Critérios de aceite**

- Nenhuma dependência declarada e não importada.
- Nenhum arquivo de página acima de ~400 linhas.
- `prefers-reduced-motion` respeitado em todo o aplicativo.
- README descreve a stack real.

---

## 25.10 Resumo

| Fase | Achados tratados | Esforço | Depende de |
|---|---|:---:|:---:|
| 1 — Tokens | A4, A7, A9, A10 | ~1 semana | — |
| 2 — Componentes | A2 | ~1,5 semana | 1 |
| 3 — Proporção e comando | A5, A6 | ~1,5 semana | 2 |
| 4 — Registro de comandos | **A1** | ~1 semana | 2 |
| 5 — Acessibilidade | **A3** | ~1 semana | 4 |
| 6 — Conteúdo por diretriz | A8 | ~0,5 semana | 2 |
| 7 — Higiene e refino | A11, A12, A13 | ~1 semana | 3, 4 |
| doc 26 — Validação | A14 | contínuo | 1 |

---

## 25.11 Riscos

| Risco | Prob. | Impacto | Mitigação |
|---|:---:|:---:|---|
| Codemods da Fase 1 causam regressão visual silenciosa | **Alta** | Alto | Referência visual **antes** de começar; um commit por categoria; comparação a cada commit |
| Migração de componente pára no meio, deixando dois padrões | Média | Alto | Fase 3 migra **por página inteira**, nunca por componente solto. Página migrada é página fechada |
| Adotar Radix muda a aparência dos controles | Média | Médio | Radix é sem estilo por padrão — o visual vem dos nossos tokens. Validar na galeria da Fase 2 |
| Reduzir a moldura sacrifica descoberta de comando | Média | Médio | Toolstrip recolhível com estado lembrado; comandos continuam alcançáveis por atalho e por tooltip |
| Registro de comandos vira indireção sem ganho | Baixa | Médio | Escopo travado no que o ribbon já aciona. Não virar barramento de eventos geral |
| Acessibilidade tratada como fase e não como critério | Média | Alto | Os 10 critérios do § 24.10 entram na definição de pronto **da Fase 2** |

---

## 25.12 O que este plano não faz

Registrado para não voltar como escopo por engano:

- **Não muda a linguagem visual.** Os cantos de 2 px, os bevels e as 13
  paletas ficam. O trabalho é de governo, não de redesenho.
- **Não introduz framework de CSS.** Tailwind, CSS-in-JS e afins estão fora: o
  problema não é o CSS, é a ausência de componentes.
- **Não mexe em backend nem em funcionalidade.** Nenhuma tarefa altera
  contrato de API.
- **Não trata as pendências de backlog do doc 22 § 22.6** (auto-updater, CI/CD,
  Alembic, validações em acervo real) — exceto os gráficos do dashboard, que
  entram na Fase 7 por serem interface.
