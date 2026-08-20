/**
 * Validação e confirmação do endereço do backend (doc 28 V-08, doc 29 §29.12).
 *
 * O que estes testes fixam: um link com `api_url` embutido não pode mudar o
 * destino das requisições sem que uma pessoa veja o host e confirme. O próprio
 * lançador ensina esse formato ao usuário, então ele foi treinado a clicar em
 * links do RSAC com `api_url` — e não tem como distinguir o legítimo do hostil.
 */

import { describe, expect, it } from 'vitest'
import {
  analisarUrlDeBackend,
  mensagemDeConfirmacao,
  UrlDeBackendInvalida,
} from './backendUrl'

describe('analisarUrlDeBackend', () => {
  it('recusa protocolo que não é HTTP', () => {
    for (const hostil of [
      'javascript:alert(1)',
      'file:///etc/passwd',
      'data:text/html,<script>alert(1)</script>',
    ]) {
      expect(() => analisarUrlDeBackend(hostil)).toThrow(UrlDeBackendInvalida)
    }
  })

  it('recusa endereço vazio ou sem forma de URL', () => {
    for (const invalido of ['', '   ', 'nao-e-url', '//sem-protocolo']) {
      expect(() => analisarUrlDeBackend(invalido)).toThrow(UrlDeBackendInvalida)
    }
  })

  it('recusa http:// fora do loopback', () => {
    // Credenciais e dados de pesquisa em texto claro pela rede.
    expect(() => analisarUrlDeBackend('http://backend.attacker.com')).toThrow(
      /sem criptografia/i
    )
  })

  it('aceita http:// no loopback, que é o app de mesa', () => {
    const destino = analisarUrlDeBackend('http://127.0.0.1:8000')
    expect(destino.classificacao).toBe('local')
    expect(destino.inseguro).toBe(false)
    expect(destino.url).toBe('http://127.0.0.1:8000/api/v1')
  })

  it('classifica túnel Cloudflare como host conhecido', () => {
    const destino = analisarUrlDeBackend('https://abc-123.trycloudflare.com')
    expect(destino.classificacao).toBe('conhecido')
    expect(destino.host).toBe('abc-123.trycloudflare.com')
  })

  it('classifica host arbitrário como desconhecido', () => {
    const destino = analisarUrlDeBackend('https://backend.attacker.com')
    expect(destino.classificacao).toBe('desconhecido')
  })

  it('não confunde sufixo forjado com host conhecido', () => {
    // `trycloudflare.com.evil.io` não é um túnel Cloudflare.
    const destino = analisarUrlDeBackend('https://trycloudflare.com.evil.io')
    expect(destino.classificacao).toBe('desconhecido')
  })

  it('normaliza o sufixo /api/v1 sem duplicá-lo', () => {
    expect(analisarUrlDeBackend('https://x.trycloudflare.com').url).toBe(
      'https://x.trycloudflare.com/api/v1'
    )
    expect(analisarUrlDeBackend('https://x.trycloudflare.com/').url).toBe(
      'https://x.trycloudflare.com/api/v1'
    )
    expect(analisarUrlDeBackend('https://x.trycloudflare.com/api/v1').url).toBe(
      'https://x.trycloudflare.com/api/v1'
    )
  })
})

describe('mensagemDeConfirmacao', () => {
  it('nomeia o host, que é a única informação que distingue o link hostil', () => {
    const destino = analisarUrlDeBackend('https://backend.attacker.com')
    const mensagem = mensagemDeConfirmacao(destino)

    expect(mensagem).toContain('backend.attacker.com')
    expect(mensagem).toContain('credenciais')
  })

  it('avisa quando o host não é um destino esperado do RSAC', () => {
    const mensagem = mensagemDeConfirmacao(analisarUrlDeBackend('https://backend.attacker.com'))
    expect(mensagem).toMatch(/não é um túnel/i)
  })

  it('não alarma para túnel legítimo', () => {
    const mensagem = mensagemDeConfirmacao(
      analisarUrlDeBackend('https://abc-123.trycloudflare.com')
    )
    expect(mensagem).not.toMatch(/⚠/)
    expect(mensagem).toContain('abc-123.trycloudflare.com')
  })
})
