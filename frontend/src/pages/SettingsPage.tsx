/**
 * RSAC V2 — Settings Page (Configurações de Inteligência Artificial & Modo Manual)
 * Gerenciamento do interruptor mestre de IA (Ativar IA vs Modo 100% Manual),
 * seleção de provedores e modelos conforme o RSAC, rotação de chaves e testes de conectividade.
 */

import { useState, useEffect } from 'react'
import {
  Settings,
  Sparkles,
  Key,
  Cpu,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Plus,
  Trash2,
  Sliders,
  Server,
  Layers,
  Globe,
  Power,
  Edit3,
  ShieldCheck,
  Palette,
  Check,
  Eye,
  EyeOff,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import type { AISettings, AISettingsUpdate } from '@/types/api'
import './SettingsPage.css'

export interface ColorThemeOption {
  id: string
  name: string
  subtitle: string
  colors: {
    c1: string
    c2: string
    c3: string
    c4: string
    c5: string
  }
}

const COLOR_THEMES: ColorThemeOption[] = [
  {
    id: 'dark',
    name: 'Organic Earth (Florestal)',
    subtitle: 'Black Forest, Olive Leaf, Cornsilk & Copperwood (Padrão)',
    colors: {
      c1: '#283618',
      c2: '#606c38',
      c3: '#fefae0',
      c4: '#dda15e',
      c5: '#bc6c25',
    },
  },
  {
    id: 'light',
    name: 'Organic Earth (Soft Warm)',
    subtitle: 'Tons quentes com fundo suave e acabamento neo-retrô',
    colors: {
      c1: '#f5f2e8',
      c2: '#283618',
      c3: '#606c38',
      c4: '#dda15e',
      c5: '#bc6c25',
    },
  },
  {
    id: 'lava-steel',
    name: 'Molten Lava & Deep Space',
    subtitle: 'Vermelho vulcânico, tijolo, papaya whip e azul espacial',
    colors: {
      c1: '#780000',
      c2: '#c1121f',
      c3: '#fdf0d5',
      c4: '#003049',
      c5: '#669bbc',
    },
  },
  {
    id: 'pastel-dream',
    name: 'Pastel Dream & Thistle',
    subtitle: 'Thistle, pétala pastel, baby pink, azul gelo e celeste',
    colors: {
      c1: '#cdb4db',
      c2: '#ffc8dd',
      c3: '#ffafcc',
      c4: '#bde0fe',
      c5: '#a2d2ff',
    },
  },
  {
    id: 'stormy-tangerine',
    name: 'Ink Black & Stormy Tangerine',
    subtitle: 'Preto nanquim, stormy teal, papaya whip, tangerina e conhaque',
    colors: {
      c1: '#001524',
      c2: '#15616d',
      c3: '#ffecd1',
      c4: '#ff7d00',
      c5: '#78290f',
    },
  },
  {
    id: 'platinum-dusk',
    name: 'Platinum & Dusk Blue',
    subtitle: 'Platina, azul crepúsculo, azul aço, azul gelo e oliva acinzentada',
    colors: {
      c1: '#e7ecef',
      c2: '#274c77',
      c3: '#6096ba',
      c4: '#a3cef1',
      c5: '#8b8c89',
    },
  },
  {
    id: 'indigo-rose',
    name: 'Indigo Bloom & Brilliant Rose',
    subtitle: 'Índigo florido, rosa brilhante, chiclete e blush suave',
    colors: {
      c1: '#642ca9',
      c2: '#ff36ab',
      c3: '#ff74d4',
      c4: '#ffb8de',
      c5: '#ffdde1',
    },
  },
  {
    id: 'amethyst-deep',
    name: 'Dark Amethyst & Royal Violet',
    subtitle: 'Ametista escura, índigo aveludado, violeta real e mauve',
    colors: {
      c1: '#10002b',
      c2: '#3c096c',
      c3: '#7b2cbf',
      c4: '#9d4edd',
      c5: '#e0aaff',
    },
  },
  {
    id: 'parchment-linen',
    name: 'Parchment & Almond Silk',
    subtitle: 'Pergaminho, linho natural, pétala em pó e seda de amêndoa',
    colors: {
      c1: '#edede9',
      c2: '#d6ccc2',
      c3: '#f5ebe0',
      c4: '#e3d5ca',
      c5: '#d5bdaf',
    },
  },
  {
    id: 'periwinkle-ice',
    name: 'Alice Blue & Baby Blue Ice',
    subtitle: 'Alice blue, lavanda suave, pervinca e azul bebê gelo',
    colors: {
      c1: '#edf2fb',
      c2: '#e2eafc',
      c3: '#ccdbfd',
      c4: '#b6ccfe',
      c5: '#abc4ff',
    },
  },
  {
    id: 'fuchsia-blush',
    name: 'Hot Fuchsia & Cotton Candy',
    subtitle: 'Fúcsia vibrante, morango silvestre, cerejeira e algodão doce',
    colors: {
      c1: '#ff0a54',
      c2: '#ff477e',
      c3: '#ff7096',
      c4: '#fbb1bd',
      c5: '#fae0e4',
    },
  },
  {
    id: 'powder-aqua',
    name: 'Powder Blush & Icy Aqua',
    subtitle: 'Blush em pó, eggshell, água gelada, azul suave e ardósia',
    colors: {
      c1: '#ffa69e',
      c2: '#faf3dd',
      c3: '#b8f2e6',
      c4: '#aed9e0',
      c5: '#5e6472',
    },
  },
  {
    id: 'synthwave-neon',
    name: 'Neon Pink & Electric Sapphire',
    subtitle: 'Cyberpunk synthwave, azul elétrico, azul energia e água celeste',
    colors: {
      c1: '#f72585',
      c2: '#7209b7',
      c3: '#480ca8',
      c4: '#4361ee',
      c5: '#4cc9f0',
    },
  },
]

// ── Modelos Exatos do RSAC ─────────────────────────────────────────────

const GEMINI_MODELS = [
  { id: 'gemini-3.6-flash', name: 'gemini-3.6-flash', desc: 'Recomendado — Alta velocidade e triagem rápida', badge: 'Recomendado' },
  { id: 'gemini-3.5-flash', name: 'gemini-3.5-flash', desc: 'Rápido e excelente para respostas estruturadas', badge: 'Flash' },
  { id: 'gemini-3.5-flash-lite', name: 'gemini-3.5-flash-lite', desc: 'Versão ultraleve e econômica', badge: 'Lite' },
]

const QWEN_MODELS = [
  { id: 'qwen3.8-max', name: 'qwen3.8-max', desc: 'Recomendado (2.4T parâmetros) — Raciocínio frontier', badge: 'Recomendado' },
  { id: 'qwen-plus', name: 'qwen-plus', desc: 'Recomendado para velocidade e economia', badge: 'Recomendado' },
  { id: 'qwen-turbo', name: 'qwen-turbo', desc: 'Ultra-rápido para grandes volumes', badge: 'Rápido' },
  { id: 'qwen-max', name: 'qwen-max', desc: 'Capacidade máxima consolidada', badge: 'Max' },
  { id: 'qwen-2.5-72b-instruct', name: 'qwen-2.5-72b-instruct', desc: '72 Bilhões de parâmetros', badge: '72B' },
  { id: 'qwen-2.5-32b-instruct', name: 'qwen-2.5-32b-instruct', desc: '32 Bilhões de parâmetros', badge: '32B' },
  { id: 'qwen-2.5-14b-instruct', name: 'qwen-2.5-14b-instruct', desc: '14 Bilhões de parâmetros', badge: '14B' },
  { id: 'qwen-2.5-7b-instruct', name: 'qwen-2.5-7b-instruct', desc: '7 Bilhões de parâmetros', badge: '7B' },
]

const QWEN_REGIONS = [
  { id: 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1', label: 'Internacional (Singapore) - dashscope-intl' },
  { id: 'https://dashscope-us.aliyuncs.com/compatible-mode/v1', label: 'EUA (Virginia) - dashscope-us' },
  { id: 'https://dashscope.aliyuncs.com/compatible-mode/v1', label: 'China (Beijing) - dashscope' },
  { id: 'https://openrouter.ai/api/v1', label: 'OpenRouter - openrouter.ai' },
]

const LOCAL_MODELS = [
  { id: 'Qwen-3.5-27B', name: 'Alibaba Qwen-3.5-27B', desc: 'Máxima inteligência & raciocínio (~16.7 GB Q4_K_M)', badge: '27B Top' },
  { id: 'Qwen-3.5-9B', name: 'Alibaba Qwen-3.5-9B', desc: 'Raciocínio avançado & multilíngue (~5.7 GB Q4_K_M)', badge: '9B' },
  { id: 'Qwen-3.5-4B', name: 'Alibaba Qwen-3.5-4B', desc: 'Equilíbrio e alta velocidade (~2.7 GB Q4_K_M)', badge: '4B' },
  { id: 'Llama-3.2-3B', name: 'Meta Llama-3.2-3B-Instruct', desc: 'Recomendado — Leve e 100% compatível (~2.0 GB)', badge: 'Recomendado' },
  { id: 'Qwen-2.5-3B', name: 'Alibaba Qwen-2.5-3B-Instruct', desc: 'Raciocínio & Português (~2.0 GB)', badge: 'Português' },
  { id: 'DeepSeek-R1-1.5B', name: 'DeepSeek-R1-Distill-Qwen-1.5B', desc: 'Raciocínio lógico ultraleve (~1.1 GB)', badge: 'Raciocínio' },
  { id: 'Phi-3.5-Mini', name: 'Microsoft Phi-3.5-mini-instruct', desc: 'Alta precisão sintetizada (~2.2 GB)', badge: '3.8B' },
  { id: 'Ternary-Bonsai-8B', name: 'Ternary-Bonsai-8B', desc: 'PrismML 1-bit (~2.2 GB)', badge: '1-bit' },
  { id: 'Ternary-Bonsai-4B', name: 'Ternary-Bonsai-4B', desc: 'PrismML 1-bit (~1.2 GB)', badge: '1-bit' },
  { id: 'qwen2.5:7b', name: 'Ollama — qwen2.5:7b', desc: 'Executado via Ollama local', badge: 'Ollama' },
  { id: 'llama3.3:70b', name: 'Ollama — llama3.3:70b', desc: 'Modelo pesado via Ollama', badge: 'Ollama 70B' },
]

const LOCAL_ENDPOINTS = [
  { url: 'http://localhost:11434/v1', label: 'Ollama (Porta 11434)' },
  { url: 'http://localhost:8080/v1', label: 'Servidor Local GGUF / llama.cpp (Porta 8080)' },
  { url: 'http://localhost:1234/v1', label: 'LM Studio (Porta 1234)' },
  { url: 'http://localhost:8000/v1', label: 'vLLM (Porta 8000)' },
]

export function SettingsPage(): JSX.Element {
  const { theme, setTheme, aiEnabled, setAiEnabled } = useSettingsStore()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Form State
  const [isAiActive, setIsAiActive] = useState(true)
  const [provider, setProvider] = useState<'gemini' | 'qwen' | 'local'>('gemini')
  const [model, setModel] = useState('gemini-3.6-flash')
  const [apiKeys, setApiKeys] = useState<string[]>([''])
  const [showKeyVisibility, setShowKeyVisibility] = useState<Record<number, boolean>>({})
  const [endpoint, setEndpoint] = useState('http://localhost:11434/v1')
  const [temperature, setTemperature] = useState(0.2)
  const [maxTokens, setMaxTokens] = useState(4096)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await api.getAISettings()
      setIsAiActive(data.ai_enabled !== false)
      setAiEnabled(data.ai_enabled !== false)
      setProvider(data.provider)
      setModel(data.model)
      if (data.api_keys && data.api_keys.length > 0) {
        setApiKeys(data.api_keys)
      } else {
        setApiKeys([''])
      }
      setEndpoint(data.endpoint || (data.provider === 'qwen' ? QWEN_REGIONS[0].id : 'http://localhost:11434/v1'))
      setTemperature(data.temperature)
      setMaxTokens(data.max_tokens)
    } catch (err) {
      console.error('Erro ao carregar configurações de IA:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleAiActive = (active: boolean) => {
    setIsAiActive(active)
    setAiEnabled(active)
    setTestResult(null)
  }

  const handleProviderChange = (newProvider: 'gemini' | 'qwen' | 'local') => {
    setProvider(newProvider)
    setTestResult(null)
    if (newProvider === 'gemini') {
      setModel('gemini-3.6-flash')
    } else if (newProvider === 'qwen') {
      setModel('qwen3.8-max')
      setEndpoint(QWEN_REGIONS[0].id)
    } else if (newProvider === 'local') {
      setModel('Llama-3.2-3B')
      setEndpoint('http://localhost:11434/v1')
    }
  }

  const handleModelPresetSelect = (presetId: string) => {
    setModel(presetId)
  }

  const addKeyField = () => {
    setApiKeys([...apiKeys, ''])
  }

  const updateKeyField = (index: number, val: string) => {
    const list = [...apiKeys]
    list[index] = val
    setApiKeys(list)
  }

  const removeKeyField = (index: number) => {
    const list = apiKeys.filter((_, i) => i !== index)
    setApiKeys(list.length ? list : [''])
  }

  const toggleKeyVisibility = (index: number) => {
    setShowKeyVisibility((prev) => ({
      ...prev,
      [index]: !prev[index],
    }))
  }

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    try {
      setSaving(true)
      const cleanKeys = apiKeys.map((k) => k.trim()).filter(Boolean)
      const finalModel = model || (provider === 'gemini' ? 'gemini-3.6-flash' : provider === 'qwen' ? 'qwen3.8-max' : 'Llama-3.2-3B')

      const updated = await api.updateAISettings({
        ai_enabled: isAiActive,
        provider,
        model: finalModel,
        api_keys: cleanKeys,
        endpoint: provider !== 'gemini' ? endpoint.trim() : null,
        temperature,
        max_tokens: maxTokens,
      })
      if (updated.api_keys && updated.api_keys.length > 0) {
        setApiKeys(updated.api_keys)
      }
      setAiEnabled(isAiActive)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      console.error('Erro ao salvar configurações de IA:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setTestResult(null)
      await handleSave()
      const res = await api.testAIConnection()
      setTestResult({
        success: true,
        message: `${res.message} (${res.provider}: ${res.model})`,
      })
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || 'Falha na conexão com o modelo de IA.',
      })
    } finally {
      setTesting(false)
    }
  }

  const currentModelList = provider === 'gemini' ? GEMINI_MODELS : provider === 'qwen' ? QWEN_MODELS : LOCAL_MODELS

  return (
    <div className="settings-page animate-fade-in">
      {/* Top Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Configurações & Modos de Operação</h1>
          <p className="page-subtitle">
            Ative ou desative recursos de Inteligência Artificial e configure modelos em nuvem ou locais
          </p>
        </div>
        <div className="header-actions">
          {saveSuccess && (
            <span className="save-indicator success">
              <CheckCircle2 size={16} /> Salvo com sucesso!
            </span>
          )}
          <button className="btn-primary" onClick={() => handleSave()} disabled={saving}>
            {saving ? 'Salvando...' : 'Salvar Alterações'}
          </button>
        </div>
      </div>

      {/* Master AI Toggle Card */}
      <div className={`master-ai-toggle-card ${isAiActive ? 'ai-active' : 'ai-disabled'}`}>
        <div className="master-toggle-info">
          <div className="master-toggle-icon">
            {isAiActive ? <Sparkles size={28} /> : <Edit3 size={28} />}
          </div>
          <div>
            <h3>{isAiActive ? 'Recursos de Inteligência Artificial Ativados' : 'Modo 100% Manual (I.A. Desativada)'}</h3>
            <p>
              {isAiActive
                ? 'A IA auxiliará na sugestão do protocolo (PICO/Critérios), triagem de estudos (Triagem 1) e extração de dados do texto integral (Triagem 2).'
                : 'Todo o processo de revisão será conduzido manualmente pelo pesquisador, ocultando botões e automações de IA para máxima conformidade e rigor manual.'}
            </p>
          </div>
        </div>

        <div className="master-toggle-buttons">
          <button
            type="button"
            className={`btn-mode-toggle ${isAiActive ? 'active' : ''}`}
            onClick={() => handleToggleAiActive(true)}
          >
            <Sparkles size={15} /> Ativar Modo I.A.
          </button>
          <button
            type="button"
            className={`btn-mode-toggle manual ${!isAiActive ? 'active' : ''}`}
            onClick={() => handleToggleAiActive(false)}
          >
            <Edit3 size={15} /> Modo 100% Manual
          </button>
        </div>
      </div>

      {/* ── Theme & Color Palette Selection Card ── */}
      <div className="settings-card theme-palette-card">
        <div className="card-section-title">
          <Palette size={20} className="icon-accent" />
          <h2>Aparência & Paletas de Cores do Sistema</h2>
        </div>
        <p className="section-help">
          Personalize a identidade visual do RSAC V2 selecionando uma das paletas de cores harmônicas projetadas para alta produtividade, contraste e leitura acadêmica prolongada.
        </p>

        <div className="themes-grid">
          {COLOR_THEMES.map((t) => {
            const isSelected =
              theme === t.id ||
              (t.id === 'dark' && (theme === 'organic-dark' || theme === 'dark')) ||
              (t.id === 'light' && (theme === 'organic-light' || theme === 'light'))
            return (
              <div
                key={t.id}
                className={`theme-card-item ${isSelected ? 'selected' : ''}`}
                onClick={() => setTheme(t.id)}
                title={`Aplicar paleta ${t.name}`}
              >
                <div className="theme-card-header">
                  <span className="theme-card-name">{t.name}</span>
                </div>
                <p className="theme-card-subtitle">{t.subtitle}</p>
                <div className="theme-color-swatches">
                  <span className="swatch" style={{ background: t.colors.c1 }} title={`Cor 1: ${t.colors.c1}`} />
                  <span className="swatch" style={{ background: t.colors.c2 }} title={`Cor 2: ${t.colors.c2}`} />
                  <span className="swatch" style={{ background: t.colors.c3 }} title={`Cor 3: ${t.colors.c3}`} />
                  <span className="swatch" style={{ background: t.colors.c4 }} title={`Cor 4: ${t.colors.c4}`} />
                  <span className="swatch" style={{ background: t.colors.c5 }} title={`Cor 5: ${t.colors.c5}`} />
                </div>
                {isSelected && (
                  <div className="theme-selected-badge">
                    <Check size={11} /> Tema Ativo
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="settings-grid" style={{ opacity: isAiActive ? 1 : 0.6 }}>
        {/* Left Column: AI Provider & Models Catalog */}
        <div className="settings-col">
          <div className="settings-card">
            <div className="card-section-title">
              <Sparkles size={20} className="icon-accent" />
              <h2>Provedor de Inteligência Artificial</h2>
            </div>
            <p className="section-help">
              Selecione o provedor e o modelo desejado para triagem, sugestão de protocolo e extração de dados.
            </p>

            {/* Provider Tabs */}
            <div className="provider-tabs">
              <button
                type="button"
                className={`provider-tab-btn ${provider === 'gemini' ? 'active' : ''}`}
                onClick={() => handleProviderChange('gemini')}
                disabled={!isAiActive}
              >
                <span className="provider-tab-title">Google Gemini</span>
                <span className="provider-tab-desc">Nuvem / Alta velocidade</span>
              </button>

              <button
                type="button"
                className={`provider-tab-btn ${provider === 'qwen' ? 'active' : ''}`}
                onClick={() => handleProviderChange('qwen')}
                disabled={!isAiActive}
              >
                <span className="provider-tab-title">Alibaba Qwen</span>
                <span className="provider-tab-desc">DashScope / OpenAI Format</span>
              </button>

              <button
                type="button"
                className={`provider-tab-btn ${provider === 'local' ? 'active' : ''}`}
                onClick={() => handleProviderChange('local')}
                disabled={!isAiActive}
              >
                <span className="provider-tab-title">Modelos Locais</span>
                <span className="provider-tab-desc">GGUF / Ollama / LM Studio</span>
              </button>
            </div>

            {/* Models Catalog List */}
            <div className="model-catalog-section">
              <label className="section-sublabel">
                <Layers size={14} /> Modelos Disponíveis para {provider === 'gemini' ? 'Google Gemini' : provider === 'qwen' ? 'Alibaba Qwen' : 'Execução Local'}
              </label>

              <div className="model-options-list">
                {currentModelList.map((m) => {
                  const active = model === m.id
                  return (
                    <div
                      key={m.id}
                      className={`model-option-card ${active ? 'selected' : ''}`}
                      onClick={() => isAiActive && handleModelPresetSelect(m.id)}
                    >
                      <div className="model-opt-header">
                        <span className="model-opt-name">{m.name}</span>
                        {m.badge && <span className="model-badge">{m.badge}</span>}
                      </div>
                      <p className="model-opt-desc">{m.desc}</p>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Qwen Regions / Base URL */}
            {provider === 'qwen' && (
              <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
                <label>
                  <Globe size={14} /> Região / Endpoint do DashScope
                </label>
                <div className="endpoint-presets">
                  {QWEN_REGIONS.map((r) => (
                    <button
                      key={r.id}
                      type="button"
                      disabled={!isAiActive}
                      className={`btn-endpoint-preset ${endpoint === r.id ? 'active' : ''}`}
                      onClick={() => setEndpoint(r.id)}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  disabled={!isAiActive}
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  placeholder="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
                  style={{ marginTop: 'var(--space-2)' }}
                />
              </div>
            )}

            {/* Local Server Endpoint Presets */}
            {provider === 'local' && (
              <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
                <label>
                  <Server size={14} /> URL do Servidor Local (OpenAI-Compatible)
                </label>
                <div className="endpoint-presets">
                  {LOCAL_ENDPOINTS.map((ep) => (
                    <button
                      key={ep.url}
                      type="button"
                      disabled={!isAiActive}
                      className={`btn-endpoint-preset ${endpoint === ep.url ? 'active' : ''}`}
                      onClick={() => setEndpoint(ep.url)}
                    >
                      {ep.label}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  disabled={!isAiActive}
                  value={endpoint}
                  onChange={(e) => setEndpoint(e.target.value)}
                  placeholder="http://localhost:11434/v1"
                  style={{ marginTop: 'var(--space-2)' }}
                />
              </div>
            )}

            {/* API Keys (for Gemini and Qwen) */}
            {provider !== 'local' && (
              <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
                <div className="label-with-action">
                  <label>Chaves de API (Rotação Automática)</label>
                  <button type="button" className="btn-text-action" onClick={addKeyField} disabled={!isAiActive}>
                    <Plus size={13} /> Adicionar outra chave
                  </button>
                </div>
                <div className="keys-list">
                  {apiKeys.map((k, idx) => (
                    <div key={idx} className="key-input-row">
                      <Key size={16} className="key-icon" />
                      <input
                        type={showKeyVisibility[idx] ? 'text' : 'password'}
                        disabled={!isAiActive}
                        placeholder={provider === 'gemini' ? 'Cole sua API Key do Google AI Studio...' : 'Cole sua API Key do DashScope...'}
                        value={k}
                        onChange={(e) => updateKeyField(idx, e.target.value)}
                      />
                      <button
                        type="button"
                        className="btn-icon"
                        onClick={() => toggleKeyVisibility(idx)}
                        disabled={!isAiActive}
                        title={showKeyVisibility[idx] ? 'Ocultar chave' : 'Exibir chave'}
                      >
                        {showKeyVisibility[idx] ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                      {apiKeys.length > 1 && (
                        <button
                          type="button"
                          className="btn-icon danger"
                          onClick={() => removeKeyField(idx)}
                          disabled={!isAiActive}
                          title="Remover chave"
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connection Test Bar */}
            <div className="test-connection-section">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleTestConnection}
                disabled={testing || !isAiActive}
              >
                {testing ? (
                  <>
                    <RefreshCw size={15} className="animate-spin" /> Testando Conexão...
                  </>
                ) : (
                  <>
                    <Cpu size={15} /> Testar Conexão com IA
                  </>
                )}
              </button>

              {testResult && (
                <div className={`test-result-badge ${testResult.success ? 'success' : 'error'}`}>
                  {testResult.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  <span>{testResult.message}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Hyperparameters & Preferences */}
        <div className="settings-col">
          <div className="settings-card">
            <div className="card-section-title">
              <Sliders size={20} className="icon-accent" />
              <h2>Hiperparâmetros de Inferência</h2>
            </div>
            <p className="section-help">
              Ajuste fino de temperatura e tamanho de contexto para a geração.
            </p>

            <div className="form-group">
              <div className="range-label-row">
                <label>Temperatura ({temperature})</label>
                <span className="range-hint">Valores baixos (0.0 - 0.3) garantem rigor e zero alucinação.</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                disabled={!isAiActive}
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
              />
            </div>

            <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
              <label>Máximo de Tokens de Saída ({maxTokens})</label>
              <select
                disabled={!isAiActive}
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value, 10))}
              >
                <option value={2048}>2.048 tokens</option>
                <option value={4096}>4.096 tokens (Padrão)</option>
                <option value={8192}>8.192 tokens</option>
                <option value={16384}>16.384 tokens (Para Extração Extensa)</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
