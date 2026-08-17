import { chromium } from 'playwright-core'
import { mkdirSync } from 'fs'
const OUT='/tmp/claude-0/-home-user-RSACV2/fe0da553-e30f-5684-98ac-e2f169b17eea/scratchpad/depois'
const PID='11612f54-b461-44d1-b0a1-db2077940744'
const TEMAS=['dark','light','lava-steel','pastel-dream','stormy-tangerine','platinum-dusk','indigo-rose',
             'amethyst-deep','parchment-linen','periwinkle-ice','fuchsia-blush','powder-aqua','synthwave-neon']
const TELAS=[['dashboard','/'],['projetos','/projects'],['protocolo',`/projects/${PID}/protocol`],
  ['coleta',`/projects/${PID}/harvest`],['triagem',`/projects/${PID}/screening`],
  ['extracao',`/projects/${PID}/extraction`],['exportar',`/projects/${PID}/export`],['config','/settings']]
mkdirSync(OUT,{recursive:true})
const b = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox'] })
const p = await b.newPage({ viewport:{width:1440,height:900} })
const errs=[]; p.on('pageerror',e=>errs.push(e.message))
for (const [tela,rota] of TELAS) {
  await p.goto(`http://localhost:5201/?port=8000#${rota}`,{waitUntil:'domcontentloaded'}); await p.waitForTimeout(2400)
  for (const t of TEMAS) {
    await p.evaluate(th=>document.documentElement.setAttribute('data-theme',th), t)
    await p.waitForTimeout(220); await p.screenshot({ path:`${OUT}/${tela}__${t}.png` })
  }
}
console.log(errs.slice(0,3).join('\n')||'sem erros de página')
await b.close()
