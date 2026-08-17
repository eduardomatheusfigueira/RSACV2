/**
 * RSAC V2 — Avisos Transitórios (sonner)
 *
 * O padrão até aqui era `alert()` do navegador para erro e um `<span>` que
 * aparecia por três segundos no cabeçalho para sucesso. O primeiro trava a
 * janela inteira; o segundo some sem que quem esteja olhando o rodapé da tela
 * chegue a vê-lo, e nenhum dos dois é anunciado por leitor de tela.
 *
 * `sonner` estava declarado no package.json desde o início e nunca foi
 * importado. Aqui ele entra com as cores da paleta ativa — as classes recebem
 * os tokens do design system em vez do tema embutido da biblioteca.
 */

import { Toaster as SonnerToaster, toast } from 'sonner'
import './Toaster.css'

export function Toaster(): JSX.Element {
  return (
    <SonnerToaster
      position="bottom-right"
      duration={4000}
      gap={8}
      toastOptions={{
        classNames: {
          toast: 'rsac-toast',
          title: 'rsac-toast__title',
          description: 'rsac-toast__description',
          actionButton: 'rsac-toast__action',
          cancelButton: 'rsac-toast__cancel',
          closeButton: 'rsac-toast__close',
          success: 'rsac-toast--success',
          error: 'rsac-toast--error',
          warning: 'rsac-toast--warning',
          info: 'rsac-toast--info',
        },
      }}
      closeButton
      /* O container do sonner já carrega aria-live; o rótulo diz de onde vêm. */
      containerAriaLabel="Avisos do RSAC"
    />
  )
}

export { toast }
