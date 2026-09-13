# Revsist — laço de abertura da landing

Vídeo programático em [Remotion](https://remotion.dev) que roda em laço no topo
de `landing/index.html`. Uma composição só, `HeroLoop`: 25 s, 1920×1080 a 30 fps,
sem áudio.

## O que ele é (e o que deliberadamente não é)

- **Sangra até a borda.** Nenhuma moldura de navegador, barra de título, sombra
  de janela ou controle de player é desenhado dentro do vídeo. As capturas de
  tela entram mascaradas por gradiente, dissolvendo no papel da página.
- **Usa as capturas reais do app**, na mesma paleta da landing. Elas são
  copiadas de `landing/src/imagens/telas/` na hora do render — ver
  *Sincronização* abaixo.
- **Emenda invisível.** O fundo (papel, grade, curvas de nível) só usa funções
  periódicas no período total, e as cenas das pontas são renderizadas duas
  vezes, deslocadas de um período. Assim o quadro 750 é idêntico ao quadro 0 e o
  laço não pisca.
- **A página é que fala.** O título e as chamadas são HTML, não pixels: o vídeo
  mostra o produto funcionando, não repete a manchete.

## Estrutura

| Arquivo | Papel |
|---|---|
| `src/theme.ts` | Paleta e grade temporal — espelha `frontend/src/styles/globals.css` |
| `src/components/base.tsx` | Fontes, atmosfera texturizada, câmera virtual, capturas e tipografia animada |
| `src/components/FluxoPrisma.tsx` | Fluxograma PRISMA 2020 desenhado quadro a quadro |
| `src/compositions/HeroLoop.tsx` | As seis cenas e a montagem do laço |
| `scripts/sincronizar-assets.mjs` | Copia capturas e fontes da landing para `public/` |

As seis cenas: abertura, coleta federada, triagem com rastro, extração
estruturada, síntese PRISMA e fecho de marca.

## Comandos

```bash
npm install
npm start              # estúdio interativo do Remotion
npm run render:mp4     # gera landing/public/videos/revsist-hero.mp4
npm run render:poster  # gera o pôster usado como cartaz e no movimento reduzido
npm run build          # os dois acima
```

O render sai em escala 0,75 (1440×810) com CRF 30: ~2,4 MB, que é o teto
razoável para um vídeo que carrega junto com a dobra inicial da página.

## Sincronização com a landing

`public/` **não é versionado**. As capturas de tela e as fontes são copiadas de
`landing/` a cada `npm start` ou render, por um passo `pre` automático.

Isso não é purismo de repositório: manter uma segunda cópia versionada foi
exatamente o que deixou o vídeo mostrando o app numa paleta que a landing já não
usava. Para atualizar as capturas, gere-as na origem — `npm run test:seed` e
`node scripts/capturar-telas-landing.mjs`, ambos em `frontend/` — e rode o
render de novo.
