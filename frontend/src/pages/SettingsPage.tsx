/**
 * RSAC V2 — Settings Page (Configurações de Inteligência Artificial, Portabilidade & Modo Manual)
 * Gerenciamento do interruptor mestre de IA (Ativar IA vs Modo 100% Manual),
 * separação estrita de chaves (Gemini vs Qwen vs Local), exportação/importação de chaves (.json / .env)
 * e backup/restauração de perfil completo de sessão e workspace.
 */

import { useState, useEffect, useRef } from 'react'
import {
  Sparkles,
  Key,
  KeyRound,
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
  Edit3,
  Palette,
  Check,
  Eye,
  EyeOff,
  Download,
  Upload,
  FolderArchive,
  FileCode,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react'
import { api } from '@/api/client'
import { useSettingsStore } from '@/stores/useSettingsStore'
import { useRibbonStore } from '@/stores/useRibbonStore'
import { RsacLockup } from '@/components/brand/RsacLockup'
import { PageHeader, Button, Card } from '@/components/ui'
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

interface ProviderKeysFieldProps {
  label: string
  hint: React.ReactNode
  placeholder: string
  /** Máscaras das chaves já guardadas no backend. */
  previews: string[]
  /** Chaves novas sendo digitadas (só existem em modo de substituição). */
  keys: string[]
  editing: boolean
  visibility: Record<number, boolean>
  disabled: boolean
  onStartEditing: () => void
  onCancelEditing: () => void
  onAdd: () => void
  onUpdate: (index: number, value: string) => void
  onRemoveField: (index: number) => void
  onToggleVisibility: (index: number) => void
  onRemoveAll: () => void
}

/**
 * Campo de chaves de API de um provedor, em duas faces.
 *
 * O backend deixou de devolver a chave em texto claro, então não há o que
 * "editar": ou se olha a máscara do que está guardado, ou se digita uma chave
 * nova por inteiro para substituir. As duas faces deste componente são
 * exatamente esses dois estados — e o caminho de apagar é separado dos dois,
 * porque salvar o formulário nunca mais destrói credencial por engano.
 */
function ProviderKeysField({
  label,
  hint,
  placeholder,
  previews,
  keys,
  editing,
  visibility,
  disabled,
  onStartEditing,
  onCancelEditing,
  onAdd,
  onUpdate,
  onRemoveField,
  onToggleVisibility,
  onRemoveAll,
}: ProviderKeysFieldProps): JSX.Element {
  const temChavesGuardadas = previews.length > 0
  const mostrandoFormulario = editing || !temChavesGuardadas

  return (
    <div className="form-group" style={{ marginTop: 'var(--space-4)' }}>
      <div className="label-with-action">
        <label>{label}</label>
        {mostrandoFormulario ? (
          <button type="button" className="btn-text-action" onClick={onAdd} disabled={disabled}>
            <Plus size={13} /> Adicionar outra chave
          </button>
        ) : (
          <button type="button" className="btn-text-action" onClick={onStartEditing} disabled={disabled}>
            <Edit3 size={13} /> Substituir chaves
          </button>
        )}
      </div>

      <p className="range-hint" style={{ marginTop: '2px', marginBottom: '6px' }}>
        {hint}
      </p>

      {!mostrandoFormulario && (
        <>
          <div className="keys-list">
            {previews.map((preview, idx) => (
              <div key={idx} className="key-input-row">
                <ShieldCheck size={16} className="key-icon" />
                <input type="text" value={preview} readOnly disabled aria-label={`Chave ${idx + 1} configurada`} />
              </div>
            ))}
          </div>
          <div className="keys-stored-actions">
            <span className="range-hint">
              {previews.length === 1
                ? '1 chave configurada e guardada no servidor.'
                : `${previews.length} chaves configuradas e guardadas no servidor.`}{' '}
              O valor completo não é exibido nem devolvido pela API.
            </span>
            <button type="button" className="btn-text-action danger" onClick={onRemoveAll} disabled={disabled}>
              <Trash2 size={13} /> Remover todas
            </button>
          </div>
        </>
      )}

      {mostrandoFormulario && (
        <>
          <div className="keys-list">
            {keys.map((k, idx) => (
              <div key={idx} className="key-input-row">
                <Key size={16} className="key-icon" />
                <input
                  type={visibility[idx] ? 'text' : 'password'}
                  disabled={disabled}
                  placeholder={placeholder}
                  value={k}
                  onChange={(e) => onUpdate(idx, e.target.value)}
                />
                <button
                  type="button"
                  className="btn-icon"
                  onClick={() => onToggleVisibility(idx)}
                  disabled={disabled}
                  title={visibility[idx] ? 'Ocultar chave' : 'Exibir chave'}
                >
                  {visibility[idx] ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
                {keys.length > 1 && (
                  <button
                    type="button"
                    className="btn-icon danger"
                    onClick={() => onRemoveField(idx)}
                    disabled={disabled}
                    title="Remover chave"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
          {temChavesGuardadas && (
            <div className="keys-stored-actions">
              <span className="range-hint">
                Ao salvar, as {previews.length} chave(s) atuais serão substituídas pelo que estiver acima.
              </span>
              <button type="button" className="btn-text-action" onClick={onCancelEditing} disabled={disabled}>
                Cancelar substituição
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}


export function SettingsPage(): JSX.Element {
  const { theme, setTheme, activeProject, setActiveProject, aiEnabled, setAiEnabled, backendVersion } = useSettingsStore()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Form State
  const [isAiActive, setIsAiActive] = useState(true)
  const [provider, setProvider] = useState<'gemini' | 'qwen' | 'local'>('gemini')
  const [model, setModel] = useState('gemini-3.6-flash')

  // Chaves Separadas por Provedor (Isolamento Estrito).
  //
  // O backend não devolve mais a chave em texto claro — devolve a máscara
  // (`••••••••abcd`). Por isso cada provedor tem dois estados: `*Previews`, o
  // que já está guardado, e `*Keys`, o que o usuário está digitando para
  // substituir. Só o segundo é enviado, e só quando ele resolve substituir.
  const [geminiPreviews, setGeminiPreviews] = useState<string[]>([])
  const [qwenPreviews, setQwenPreviews] = useState<string[]>([])
  const [localPreviews, setLocalPreviews] = useState<string[]>([])

  const [geminiKeys, setGeminiKeys] = useState<string[]>([''])
  const [qwenKeys, setQwenKeys] = useState<string[]>([''])
  const [localKeys, setLocalKeys] = useState<string[]>([''])

  const [editingGeminiKeys, setEditingGeminiKeys] = useState(false)
  const [editingQwenKeys, setEditingQwenKeys] = useState(false)
  const [editingLocalKeys, setEditingLocalKeys] = useState(false)

  const [showGeminiVisibility, setShowGeminiVisibility] = useState<Record<number, boolean>>({})
  const [showQwenVisibility, setShowQwenVisibility] = useState<Record<number, boolean>>({})
  const [showLocalVisibility, setShowLocalVisibility] = useState<Record<number, boolean>>({})

  const [endpoint, setEndpoint] = useState('http://localhost:11434/v1')
  const [temperature, setTemperature] = useState(0.2)
  const [maxTokens, setMaxTokens] = useState(4096)

  // Scientific Sources Credentials State
  const [sourceCreds, setSourceCreds] = useState<import('@/types/api').SourceCredential[]>([])
  const [scopusKey, setScopusKey] = useState('')
  const [scopusInstToken, setScopusInstToken] = useState('')
  const [pubmedKey, setPubmedKey] = useState('')
  const [openalexEmail, setOpenalexEmail] = useState('')
  const [savingSourceCreds, setSavingSourceCreds] = useState(false)
  const [sourceSaveSuccess, setSourceSaveSuccess] = useState(false)

  // Portability States (Keys & Profile Backup/Restore)
  const [exportingKeys, setExportingKeys] = useState(false)
  const [importingKeys, setImportingKeys] = useState(false)
  const [keysImportResult, setKeysImportResult] = useState<{ success: boolean; message: string; details?: string } | null>(null)

  const [exportingProfile, setExportingProfile] = useState(false)
  const [importingProfile, setImportingProfile] = useState(false)
  const [profileImportResult, setProfileImportResult] = useState<{ success: boolean; message: string; details?: string } | null>(null)

  const keysFileInputRef = useRef<HTMLInputElement>(null)
  const profileFileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const [data, creds] = await Promise.all([
        api.getAISettings(),
        api.getSourceCredentials().catch(() => []),
      ])

      setIsAiActive(data.ai_enabled !== false)
      setAiEnabled(data.ai_enabled !== false)
      setProvider(data.provider)
      setModel(data.model)

      // Preencher as máscaras das chaves guardadas e sair do modo de edição
      applyKeyPreviews(data)

      setEndpoint(data.endpoint || (data.provider === 'qwen' ? QWEN_REGIONS[0].id : 'http://localhost:11434/v1'))
      setTemperature(data.temperature)
      setMaxTokens(data.max_tokens)
      setSourceCreds(creds || [])
    } catch (err) {
      console.error('Erro ao carregar configurações:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSourceCredentials = async () => {
    try {
      setSavingSourceCreds(true)
      if (scopusKey || scopusInstToken) {
        await api.updateSourceCredential('Scopus', {
          api_key: scopusKey || undefined,
          inst_token: scopusInstToken || undefined,
        })
      }
      if (pubmedKey) {
        await api.updateSourceCredential('PubMed', {
          api_key: pubmedKey,
        })
      }
      if (openalexEmail) {
        await api.updateSourceCredential('OpenAlex', {
          api_key: openalexEmail,
        })
      }
      const updatedCreds = await api.getSourceCredentials()
      setSourceCreds(updatedCreds)
      setScopusKey('')
      setScopusInstToken('')
      setPubmedKey('')
      setOpenalexEmail('')
      setSourceSaveSuccess(true)
      setTimeout(() => setSourceSaveSuccess(false), 3000)
    } catch (err: any) {
      console.error('Erro ao salvar credenciais das fontes:', err)
    } finally {
      setSavingSourceCreds(false)
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

  /**
   * Reflete o estado das chaves vindo do backend: exibe as máscaras e encerra
   * o modo de substituição, limpando o que estava digitado.
   */
  const applyKeyPreviews = (data: import('@/types/api').AISettings) => {
    setGeminiPreviews(data.gemini_key_previews || [])
    setQwenPreviews(data.qwen_key_previews || [])
    setLocalPreviews(data.local_key_previews || [])

    setGeminiKeys([''])
    setQwenKeys([''])
    setLocalKeys([''])

    setEditingGeminiKeys(false)
    setEditingQwenKeys(false)
    setEditingLocalKeys(false)

    setShowGeminiVisibility({})
    setShowQwenVisibility({})
    setShowLocalVisibility({})
  }

  /** Remoção explícita — o salvamento comum nunca apaga chave. */
  const handleRemoveProviderKeys = async (target: 'gemini' | 'qwen' | 'local') => {
    const rotulo = target === 'gemini' ? 'Google Gemini' : target === 'qwen' ? 'Alibaba Qwen' : 'Local/OpenRouter'
    if (!window.confirm(`Remover todas as chaves de ${rotulo}? Esta ação não pode ser desfeita.`)) return
    try {
      const updated = await api.deleteProviderKeys(target)
      applyKeyPreviews(updated)
    } catch (err) {
      console.error('Erro ao remover chaves do provedor:', err)
    }
  }

  // ── Gemini Key Handlers ─────────────────────────────────────────────
  const addGeminiKeyField = () => setGeminiKeys([...geminiKeys, ''])
  const updateGeminiKeyField = (index: number, val: string) => {
    const list = [...geminiKeys]
    list[index] = val
    setGeminiKeys(list)
  }
  const removeGeminiKeyField = (index: number) => {
    const list = geminiKeys.filter((_, i) => i !== index)
    setGeminiKeys(list.length ? list : [''])
  }
  const toggleGeminiKeyVisibility = (index: number) => {
    setShowGeminiVisibility((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  // ── Qwen Key Handlers ───────────────────────────────────────────────
  const addQwenKeyField = () => setQwenKeys([...qwenKeys, ''])
  const updateQwenKeyField = (index: number, val: string) => {
    const list = [...qwenKeys]
    list[index] = val
    setQwenKeys(list)
  }
  const removeQwenKeyField = (index: number) => {
    const list = qwenKeys.filter((_, i) => i !== index)
    setQwenKeys(list.length ? list : [''])
  }
  const toggleQwenKeyVisibility = (index: number) => {
    setShowQwenVisibility((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  // ── Local Key Handlers ──────────────────────────────────────────────
  const addLocalKeyField = () => setLocalKeys([...localKeys, ''])
  const updateLocalKeyField = (index: number, val: string) => {
    const list = [...localKeys]
    list[index] = val
    setLocalKeys(list)
  }
  const removeLocalKeyField = (index: number) => {
    const list = localKeys.filter((_, i) => i !== index)
    setLocalKeys(list.length ? list : [''])
  }
  const toggleLocalKeyVisibility = (index: number) => {
    setShowLocalVisibility((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    try {
      setSaving(true)
      // Só sobe a chave que o usuário digitou de propósito. Provedor que não
      // entrou em modo de substituição nem vai no corpo da requisição — é
      // assim que salvar o formulário deixa de poder apagar credencial.
      const keysToSend = (editing: boolean, fields: string[]): string[] | undefined => {
        if (!editing) return undefined
        const clean = fields.map((k) => k.trim()).filter(Boolean)
        return clean.length > 0 ? clean : undefined
      }

      const finalModel = model || (provider === 'gemini' ? 'gemini-3.6-flash' : provider === 'qwen' ? 'qwen3.8-max' : 'Llama-3.2-3B')

      const updated = await api.updateAISettings({
        ai_enabled: isAiActive,
        provider,
        model: finalModel,
        gemini_api_keys: keysToSend(editingGeminiKeys, geminiKeys),
        qwen_api_keys: keysToSend(editingQwenKeys, qwenKeys),
        local_api_keys: keysToSend(editingLocalKeys, localKeys),
        endpoint: provider !== 'gemini' ? endpoint.trim() : null,
        temperature,
        max_tokens: maxTokens,
      })

      applyKeyPreviews(updated)

      setAiEnabled(isAiActive)
      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)
    } catch (err) {
      console.error('Erro ao salvar configurações de assistência:', err)
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
        message: err.message || 'Falha na conexão com o serviço de assistência.',
      })
    } finally {
      setTesting(false)
    }
  }

  // ── Sincronização de Ações com o Ribbon Bar ─────────────────────────
  const registerRibbonActions = useRibbonStore((s) => s.registerActions)
  const unregisterRibbonActions = useRibbonStore((s) => s.unregisterActions)

  useEffect(() => {
    registerRibbonActions({
      testConnection: handleTestConnection,
      saveSettings: () => handleSave(),
      isTestingSettings: testing,
      isSavingSettings: saving,
    })
    return () => {
      unregisterRibbonActions([
        'testConnection',
        'saveSettings',
        'isTestingSettings',
        'isSavingSettings',
      ])
    }
  }, [
    registerRibbonActions,
    unregisterRibbonActions,
    handleTestConnection,
    handleSave,
    testing,
    saving,
  ])

  // ── Helper para Download de Arquivos JSON ───────────────────────────
  const downloadJsonFile = (filename: string, data: any) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // ── Exportação & Importação de Chaves de API ────────────────────────

  /**
   * O arquivo de chaves passou a ser cifrado com uma senha escolhida na hora.
   * Sem a senha o backup é inútil — inclusive para quem o encontrar na pasta
   * de downloads ou numa pasta sincronizada com a nuvem.
   */
  const handleExportKeys = async () => {
    const senha = window.prompt(
      'Defina uma senha para proteger o arquivo de chaves (mínimo 8 caracteres).\n' +
        'Você precisará dela para restaurar este backup — guarde-a em local seguro.'
    )
    if (senha === null) return
    if (senha.trim().length < 8) {
      setKeysImportResult({
        success: false,
        message: 'A senha de exportação precisa ter ao menos 8 caracteres.',
      })
      return
    }

    try {
      setExportingKeys(true)
      setKeysImportResult(null)
      const data = await api.exportKeys(senha.trim())
      const dateStr = new Date().toISOString().slice(0, 10)
      downloadJsonFile(`rsac-chaves-api-${dateStr}.rsackeys.json`, data)
      setKeysImportResult({
        success: true,
        message: 'Arquivo de chaves exportado e cifrado com a senha informada.',
        details: 'Guarde a senha: sem ela o arquivo não pode ser restaurado.',
      })
    } catch (err: any) {
      console.error('Erro ao exportar chaves:', err)
      setKeysImportResult({
        success: false,
        message: err.message || 'Falha ao exportar as chaves de API.',
      })
    } finally {
      setExportingKeys(false)
    }
  }

  const handleImportKeysFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setImportingKeys(true)
      setKeysImportResult(null)
      const text = await file.text()
      let payload: any = null
      let rawContent: string | undefined
      try {
        payload = JSON.parse(text)
      } catch {
        rawContent = text
      }

      // Arquivo cifrado pede a senha usada na exportação.
      let exportPassword: string | undefined
      if (payload?.schema_version === 'rsac_encrypted_envelope_v1') {
        const senha = window.prompt('Este arquivo está protegido. Informe a senha usada na exportação:')
        if (senha === null) {
          setImportingKeys(false)
          e.target.value = ''
          return
        }
        exportPassword = senha
      }

      const res = await api.importKeys(payload, { rawContent, exportPassword })
      await loadSettings()
      setKeysImportResult({
        success: true,
        message: res.message,
        details: `Google Gemini: ${res.gemini_keys_count} chaves | Alibaba Qwen: ${res.qwen_keys_count} chaves | Bases científicas: ${res.sources_configured.join(', ') || 'Nenhuma'}`,
      })
    } catch (err: any) {
      setKeysImportResult({
        success: false,
        message: err.message || 'Falha ao importar arquivo de chaves de API.',
      })
    } finally {
      setImportingKeys(false)
      e.target.value = ''
    }
  }

  // ── Exportação & Importação de Perfil Completo ───────────────────────
  const handleExportProfile = async () => {
    try {
      setExportingProfile(true)
      const profile = await api.exportProfile({
        theme,
        active_project_id: activeProject?.id,
        sidebar_collapsed: false,
        ai_enabled: isAiActive,
      })
      const dateStr = new Date().toISOString().slice(0, 10)
      downloadJsonFile(`rsac-perfil-backup-${dateStr}.json`, profile)
    } catch (err: any) {
      console.error('Erro ao exportar perfil completo:', err)
    } finally {
      setExportingProfile(false)
    }
  }

  const handleImportProfileFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      setImportingProfile(true)
      setProfileImportResult(null)
      const text = await file.text()
      const profileData = JSON.parse(text)
      const res = await api.importProfile(profileData)

      if (res.restored_session?.theme) {
        setTheme(res.restored_session.theme)
      }
      await loadSettings()

      // Se havia um projeto ativo no perfil importado, tentar recarregá-lo
      if (res.restored_session?.active_project_id) {
        api.getProject(res.restored_session.active_project_id)
          .then((p) => setActiveProject(p))
          .catch(() => {})
      }

      setProfileImportResult({
        success: true,
        message: res.message,
        details: `${res.projects_imported} projetos, ${res.papers_imported} artigos e ${res.extractions_imported} extrações restaurados com sucesso.`,
      })
    } catch (err: any) {
      setProfileImportResult({
        success: false,
        message: err.message || 'Falha ao restaurar perfil completo. Verifique se o arquivo JSON é válido.',
      })
    } finally {
      setImportingProfile(false)
      e.target.value = ''
    }
  }

  const currentModelList = provider === 'gemini' ? GEMINI_MODELS : provider === 'qwen' ? QWEN_MODELS : LOCAL_MODELS

  return (
    <div className="settings-page animate-fade-in">
      <PageHeader
        title="Configurações & Portabilidade"
        subtitle="Gerencie chaves de API isoladas por provedor, exporte/importe credenciais e salve perfis completos de workspace"
        status={
          saveSuccess && (
            <span className="save-indicator success animate-fade-in" role="status" aria-live="polite">
              <CheckCircle2 size={13} aria-hidden="true" /> Salvo com sucesso!
            </span>
          )
        }
        primaryAction={
          <Button variant="primary" size="md" onClick={() => handleSave()} loading={saving}>
            {saving ? 'Salvando…' : 'Salvar Alterações'}
          </Button>
        }
      />

      {/* Master AI Toggle Card */}
      <Card className={`master-ai-toggle-card ${isAiActive ? 'ai-active' : 'ai-disabled'}`}>
        <div className="master-toggle-info">
          <div className="master-toggle-icon">
            {isAiActive ? <Sparkles size={28} /> : <Edit3 size={28} />}
          </div>
          <div>
            <h3>{isAiActive ? 'Recursos de Assistência Ativos' : 'Modo Manual'}</h3>
            <p>
              {isAiActive
                ? 'A assistência auxilia na sugestão de protocolo, triagem de estudos e extração de dados conforme o padrão RSAC.'
                : 'O processo de revisão é conduzido integralmente pelo pesquisador, sem chamadas externas a modelos.'}
            </p>
          </div>
        </div>

        <div className="master-toggle-buttons">
          <button
            type="button"
            className={`btn-mode-toggle ${isAiActive ? 'active' : ''}`}
            onClick={() => handleToggleAiActive(true)}
          >
            <Sparkles size={15} /> Modo Assistido
          </button>
          <button
            type="button"
            className={`btn-mode-toggle manual ${!isAiActive ? 'active' : ''}`}
            onClick={() => handleToggleAiActive(false)}
          >
            <Edit3 size={15} /> Modo Manual
          </button>
        </div>
      </Card>

      {/* ── SEÇÃO DE PORTABILIDADE: CHAVES & PERFIL COMPLETO ── */}
      <Card className="settings-card portability-section">
        <div className="card-section-title">
          <FolderArchive size={20} className="icon-accent" />
          <h2>Portabilidade & Transferência entre Computadores</h2>
        </div>
        <p className="section-help">
          Utilize as ferramentas abaixo para migrar suas configurações e projetos para qualquer outro computador com o app instalado.
        </p>

        <div className="portability-cards-grid">
          {/* Card 1: Chaves de API */}
          <Card surface="primaria" className="portability-card">
            <div className="portability-header">
              <div className="portability-icon">
                <KeyRound size={22} />
              </div>
              <div className="portability-info">
                <h3>Arquivo de Chaves de API</h3>
                <p>
                  Salva e carrega um arquivo estruturado padronizado (<code>.json</code> ou <code>.env</code>) contendo suas chaves do Google Gemini, Alibaba Qwen, Scopus, PubMed e OpenAlex.
                </p>
              </div>
            </div>

            {keysImportResult && (
              <div className={`portability-result-box ${keysImportResult.success ? 'success' : 'error'} animate-fade-in`}>
                {keysImportResult.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <div>
                  <strong>{keysImportResult.message}</strong>
                  {keysImportResult.details && <div className="portability-result-details">{keysImportResult.details}</div>}
                </div>
              </div>
            )}

            <div className="portability-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleExportKeys}
                disabled={exportingKeys}
                title="Baixar arquivo JSON com todas as chaves cadastradas"
              >
                {exportingKeys ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
                Exportar Chaves (.json)
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={() => keysFileInputRef.current?.click()}
                disabled={importingKeys}
                title="Carregar arquivo de chaves salvo em outro computador"
              >
                {importingKeys ? <RefreshCw size={14} className="animate-spin" /> : <Upload size={14} />}
                Importar Chaves (.json / .env)
              </button>
              <input
                type="file"
                ref={keysFileInputRef}
                className="file-input-hidden"
                accept=".json,.env,.txt"
                onChange={handleImportKeysFile}
              />
            </div>
          </Card>

          {/* Card 2: Perfil Completo */}
          <Card surface="primaria" className="portability-card">
            <div className="portability-header">
              <div className="portability-icon">
                <FolderArchive size={22} />
              </div>
              <div className="portability-info">
                <h3>Perfil Completo (Workspace & Sessão)</h3>
                <p>
                  Exporta e restaura o ecossistema integral: tema visual, modo de IA, chaves, credenciais de bases e todos os seus projetos com protocolos, critérios, artigos e extrações.
                </p>
              </div>
            </div>

            {profileImportResult && (
              <div className={`portability-result-box ${profileImportResult.success ? 'success' : 'error'} animate-fade-in`}>
                {profileImportResult.success ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <div>
                  <strong>{profileImportResult.message}</strong>
                  {profileImportResult.details && <div className="portability-result-details">{profileImportResult.details}</div>}
                </div>
              </div>
            )}

            <div className="portability-actions">
              <button
                type="button"
                className="btn-secondary"
                onClick={handleExportProfile}
                disabled={exportingProfile}
                title="Exportar perfil completo contendo projetos, artigos e configurações"
              >
                {exportingProfile ? <RefreshCw size={14} className="animate-spin" /> : <Download size={14} />}
                Exportar Perfil Completo (.json)
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={() => profileFileInputRef.current?.click()}
                disabled={importingProfile}
                title="Restaurar perfil completo em um novo PC"
              >
                {importingProfile ? <RefreshCw size={14} className="animate-spin" /> : <Upload size={14} />}
                Importar Perfil Completo (.json)
              </button>
              <input
                type="file"
                ref={profileFileInputRef}
                className="file-input-hidden"
                accept=".json"
                onChange={handleImportProfileFile}
              />
            </div>
          </Card>
        </div>
      </Card>

      {/* ── Theme & Color Palette Selection Card ── */}
      <Card className="settings-card theme-palette-card">
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
              <button
                type="button"
                key={t.id}
                className={`theme-card-item ${isSelected ? 'selected' : ''}`}
                onClick={() => setTheme(t.id)}
                title={`Aplicar paleta ${t.name}`}
                aria-pressed={isSelected}
              >
                <div className="theme-card-header">
                  <span className="theme-card-name">{t.name}</span>
                </div>
                <p className="theme-card-subtitle">{t.subtitle}</p>
                <div className="theme-color-swatches" aria-label="Amostras de cores do tema">
                  <span className="swatch" style={{ backgroundColor: t.colors.c1 }} title={`Cor 1: ${t.colors.c1}`} />
                  <span className="swatch" style={{ backgroundColor: t.colors.c2 }} title={`Cor 2: ${t.colors.c2}`} />
                  <span className="swatch" style={{ backgroundColor: t.colors.c3 }} title={`Cor 3: ${t.colors.c3}`} />
                  <span className="swatch" style={{ backgroundColor: t.colors.c4 }} title={`Cor 4: ${t.colors.c4}`} />
                  <span className="swatch" style={{ backgroundColor: t.colors.c5 }} title={`Cor 5: ${t.colors.c5}`} />
                </div>
                {isSelected && (
                  <div className="theme-selected-badge">
                    <Check size={11} aria-hidden="true" /> Tema Ativo
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* ── Identidade visual: a marca acompanha a paleta ativa ── */}
        <div className="brand-identity-strip">
          <RsacLockup size="lg" tone="auto" />
          <div className="brand-identity-meta">
            <p className="brand-identity-note">
              O monograma <strong>R-Lupa</strong> — cujo laço é a lente e cuja perna diagonal
              é o cabo — se re-pigmenta com a paleta selecionada acima: haste e lente seguem
              a cor do texto, o cabo segue a cor de acento do tema.
            </p>
            <div className="brand-identity-facts">
              <span className="brand-fact">
                <span className="brand-fact-label">Backend</span>
                <span className="brand-fact-value">{backendVersion || '—'}</span>
              </span>
              <span className="brand-fact">
                <span className="brand-fact-label">Estágio</span>
                <span className="brand-fact-value">Beta em desenvolvimento</span>
              </span>
              <span className="brand-fact">
                <span className="brand-fact-label">Paletas</span>
                <span className="brand-fact-value">{COLOR_THEMES.length} temas</span>
              </span>
            </div>
          </div>
        </div>
      </Card>

      <div className="settings-grid" style={{ opacity: isAiActive ? 1 : 0.6 }}>
        {/* Left Column: AI Provider & Models Catalog */}
        <div className="settings-col">
          <Card className="settings-card">
            <div className="card-section-title">
              <Sparkles size={20} className="icon-accent" />
              <h2>Provedor de Assistência</h2>
            </div>
            <p className="section-help">
              Selecione o provedor e o modelo desejado. Cada provedor possui seu conjunto independente de chaves de API.
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
                <span className="provider-tab-desc">Google AI Studio</span>
              </button>

              <button
                type="button"
                className={`provider-tab-btn ${provider === 'qwen' ? 'active' : ''}`}
                onClick={() => handleProviderChange('qwen')}
                disabled={!isAiActive}
              >
                <span className="provider-tab-title">Alibaba Qwen</span>
                <span className="provider-tab-desc">DashScope / OpenRouter</span>
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
                    <button
                      type="button"
                      key={m.id}
                      className={`model-option-card ${active ? 'selected' : ''}`}
                      onClick={() => handleModelPresetSelect(m.id)}
                      disabled={!isAiActive}
                      aria-pressed={active}
                    >
                      <div className="model-opt-header">
                        <span className="model-opt-name">{m.name}</span>
                        {m.badge && <span className="model-badge">{m.badge}</span>}
                      </div>
                      <span className="model-opt-desc">{m.desc}</span>
                    </button>
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

            {/* ── CHAVES DO PROVEDOR ATIVO ── */}
            {provider === 'gemini' && (
              <ProviderKeysField
                label="Chaves de API do Google Gemini (AI Studio)"
                hint={
                  <>
                    Chaves do Google AI Studio (iniciam com <code>AIzaSy...</code>). Permite rotação entre múltiplas chaves.
                  </>
                }
                placeholder="Cole sua API Key do Google AI Studio (AIzaSy...)"
                previews={geminiPreviews}
                keys={geminiKeys}
                editing={editingGeminiKeys}
                visibility={showGeminiVisibility}
                disabled={!isAiActive}
                onStartEditing={() => setEditingGeminiKeys(true)}
                onCancelEditing={() => {
                  setEditingGeminiKeys(false)
                  setGeminiKeys([''])
                }}
                onAdd={addGeminiKeyField}
                onUpdate={updateGeminiKeyField}
                onRemoveField={removeGeminiKeyField}
                onToggleVisibility={toggleGeminiKeyVisibility}
                onRemoveAll={() => handleRemoveProviderKeys('gemini')}
              />
            )}

            {provider === 'qwen' && (
              <ProviderKeysField
                label="Chaves de API do Alibaba Qwen (DashScope / OpenRouter)"
                hint={
                  <>
                    Chaves do Alibaba Cloud DashScope (iniciam com <code>sk-...</code>) ou chave do OpenRouter.
                  </>
                }
                placeholder="Cole sua API Key do DashScope ou OpenRouter (sk-...)"
                previews={qwenPreviews}
                keys={qwenKeys}
                editing={editingQwenKeys}
                visibility={showQwenVisibility}
                disabled={!isAiActive}
                onStartEditing={() => setEditingQwenKeys(true)}
                onCancelEditing={() => {
                  setEditingQwenKeys(false)
                  setQwenKeys([''])
                }}
                onAdd={addQwenKeyField}
                onUpdate={updateQwenKeyField}
                onRemoveField={removeQwenKeyField}
                onToggleVisibility={toggleQwenKeyVisibility}
                onRemoveAll={() => handleRemoveProviderKeys('qwen')}
              />
            )}

            {provider === 'local' && (
              <ProviderKeysField
                label="Token / Chave de Autenticação Local (Opcional)"
                hint={
                  <>
                    Geralmente não exigido para Ollama/LM Studio padrão, mas pode ser configurado para servidores protegidos por Bearer Token.
                  </>
                }
                placeholder="Bearer token local ou deixe em branco para Ollama"
                previews={localPreviews}
                keys={localKeys}
                editing={editingLocalKeys}
                visibility={showLocalVisibility}
                disabled={!isAiActive}
                onStartEditing={() => setEditingLocalKeys(true)}
                onCancelEditing={() => {
                  setEditingLocalKeys(false)
                  setLocalKeys([''])
                }}
                onAdd={addLocalKeyField}
                onUpdate={updateLocalKeyField}
                onRemoveField={removeLocalKeyField}
                onToggleVisibility={toggleLocalKeyVisibility}
                onRemoveAll={() => handleRemoveProviderKeys('local')}
              />
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
                    <Cpu size={15} /> Testar Conexão da Assistência
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
          </Card>
        </div>

        {/* Right Column: Hyperparameters & Preferences */}
        <div className="settings-col">
          <Card className="settings-card">
            <div className="card-section-title">
              <Sliders size={20} className="icon-accent" />
              <h2>Hiperparâmetros de Inferência</h2>
            </div>
            <p className="section-help">
              Ajuste fino de temperatura e tamanho de contexto para a geração.
            </p>

            <div className="form-group">
              <div className="range-label-row">
                <label htmlFor="cfg-temperature">Temperatura ({temperature})</label>
                <span className="range-hint" id="cfg-temperature-hint">
                  Valores baixos (0.0 - 0.3) garantem rigor e zero alucinação.
                </span>
              </div>
              <input
                id="cfg-temperature"
                aria-describedby="cfg-temperature-hint"
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
              <label htmlFor="cfg-max-tokens">Máximo de Tokens de Saída ({maxTokens})</label>
              <select
                id="cfg-max-tokens"
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
          </Card>

          {/* Scientific Sources Credentials Card */}
          <Card className="settings-card" style={{ marginTop: 'var(--space-4)' }}>
            <div className="card-section-title">
              <Globe size={20} className="icon-accent" />
              <h2>Credenciais de Bases Científicas</h2>
            </div>
            <p className="section-help">
              Configure chaves de API e tokens para desbloquear bases restritas (Scopus) ou acelerar taxas de requisição (PubMed, OpenAlex). As chaves são salvas com segurança no banco local.
            </p>

            <div className="form-group" style={{ marginTop: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label><strong>Scopus (Elsevier)</strong> — API Key</label>
                {sourceCreds.find((c) => c.source_name === 'SCOPUS')?.has_api_key && (
                  <span className="status-badge completed" style={{ fontSize: '11px' }}>
                    Configurada ({sourceCreds.find((c) => c.source_name === 'SCOPUS')?.key_preview})
                  </span>
                )}
              </div>
              <input
                type="password"
                placeholder="Cole sua Elsevier API Key..."
                value={scopusKey}
                onChange={(e) => setScopusKey(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label><strong>Scopus</strong> — Institutional Token (Opcional)</label>
                {sourceCreds.find((c) => c.source_name === 'SCOPUS')?.has_inst_token && (
                  <span className="status-badge completed" style={{ fontSize: '11px' }}>
                    Token Ativo ({sourceCreds.find((c) => c.source_name === 'SCOPUS')?.inst_token_preview})
                  </span>
                )}
              </div>
              <input
                type="password"
                placeholder="Cole seu Institutional Token (se sua universidade fornecer)..."
                value={scopusInstToken}
                onChange={(e) => setScopusInstToken(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label><strong>PubMed (NCBI)</strong> — API Key (Opcional)</label>
                {sourceCreds.find((c) => c.source_name === 'PUBMED')?.has_api_key && (
                  <span className="status-badge completed" style={{ fontSize: '11px' }}>
                    Configurada ({sourceCreds.find((c) => c.source_name === 'PUBMED')?.key_preview})
                  </span>
                )}
              </div>
              <input
                type="password"
                placeholder="Cole sua NCBI API Key (aumenta limite de 3 para 10 req/s)..."
                value={pubmedKey}
                onChange={(e) => setPubmedKey(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ marginTop: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label><strong>OpenAlex</strong> — E-mail para Polite Pool (Opcional)</label>
                {sourceCreds.find((c) => c.source_name === 'OPENALEX')?.has_api_key && (
                  <span className="status-badge completed" style={{ fontSize: '11px' }}>
                    Configurado ({sourceCreds.find((c) => c.source_name === 'OPENALEX')?.key_preview})
                  </span>
                )}
              </div>
              <input
                type="email"
                placeholder="seu.email@universidade.edu.br"
                value={openalexEmail}
                onChange={(e) => setOpenalexEmail(e.target.value)}
              />
            </div>

            <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleSaveSourceCredentials}
                disabled={savingSourceCreds || (!scopusKey && !scopusInstToken && !pubmedKey && !openalexEmail)}
              >
                {savingSourceCreds ? 'Salvando...' : 'Salvar Credenciais de Bases'}
              </button>
              {sourceSaveSuccess && (
                <span className="save-indicator success" style={{ fontSize: '12px' }}>
                  <CheckCircle2 size={14} /> Salvo!
                </span>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
