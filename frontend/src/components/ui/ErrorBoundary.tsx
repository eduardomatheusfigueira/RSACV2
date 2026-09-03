import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from './Button'
import { Card } from './Card'

interface Props {
  children: ReactNode
  fallbackTitle?: string
  fallbackMessage?: string
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary capturou um erro:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 flex flex-col items-center justify-center min-h-[300px]">
          <Card surface="secundaria" relief="elevado" className="max-w-xl w-full p-6 text-center space-y-4">
            <div className="inline-flex p-3 rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle size={32} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-foreground">
                {this.props.fallbackTitle || 'Ocorreu um erro nesta seção'}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {this.props.fallbackMessage ||
                  'Um problema inesperado impediu a renderização deste componente.'}
              </p>
              {this.state.error && (
                <div className="mt-3 p-3 bg-muted rounded text-xs font-mono text-left text-muted-foreground overflow-auto max-h-32">
                  {this.state.error.message || String(this.state.error)}
                </div>
              )}
            </div>
            <div className="pt-2 flex justify-center gap-3">
              <Button
                variant="primary"
                size="sm"
                onClick={this.handleReset}
                leftIcon={<RefreshCw size={14} />}
              >
                Tentar Novamente
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => window.location.reload()}
              >
                Recarregar Página
              </Button>
            </div>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}
