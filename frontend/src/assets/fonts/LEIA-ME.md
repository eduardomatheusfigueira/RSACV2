# Fontes empacotadas

Arquivos `.woff2` das famílias usadas pelo design system, servidos do próprio
aplicativo em vez do CDN do Google Fonts.

| Arquivo | Família | Eixo | Subconjunto |
|---|---|---|---|
| `inter-latin.woff2` | Inter | variável, peso 300–700 | latin |
| `inter-latin-ext.woff2` | Inter | variável, peso 300–700 | latin-ext |
| `jetbrains-mono-latin.woff2` | JetBrains Mono | variável, peso 400–700 | latin |
| `jetbrains-mono-latin-ext.woff2` | JetBrains Mono | variável, peso 400–700 | latin-ext |

**Por que empacotadas.** O `index.html` carregava a folha de estilo do
`fonts.googleapis.com` com `<link rel="stylesheet">`, que bloqueia a pintura da
página. Num aplicativo de mesa isso significa que a primeira tela dependia de
DNS e de uma viagem à internet — numa rede lenta, ou atrás de um portal
cativo, a janela ficava em branco até o navegador desistir. Servidas do disco,
as fontes aparecem no primeiro quadro e o app funciona igual sem rede.

**Licença.** Ambas as famílias são distribuídas sob a SIL Open Font License
1.1, que permite a redistribuição embutida:

- Inter — Rasmus Andersson — <https://github.com/rsms/inter>
- JetBrains Mono — JetBrains s.r.o. — <https://github.com/JetBrains/JetBrainsMono>

**Como atualizar.** Baixe o `.woff2` correspondente indicado pelo CSS do
Google Fonts (`https://fonts.googleapis.com/css2?family=Inter:wght@300..700&family=JetBrains+Mono:wght@400..700`)
com um agente de usuário moderno e substitua o arquivo mantendo o nome. Os
`@font-face` ficam em `src/styles/globals.css`.
