# 11 — Testes e Qualidade

> Estratégia de testes unitários, integração, E2E, linting e CI/CD.

---

## 11.1 Pirâmide de Testes

```
                 ┌────────────┐
                 │   E2E      │  Playwright (Electron)
                 │   (poucos) │
                ┌┴────────────┴┐
                │ Integração   │  FastAPI TestClient + SQLite in-memory
                │ (moderados)  │
               ┌┴──────────────┴┐
               │  Unitários      │  pytest + Vitest
               │  (muitos)       │
               └────────────────┘
```

---

## 11.2 Testes Backend (Python)

### Framework: pytest + pytest-asyncio

### 11.2.1 Fixtures Globais

```python
# tests/conftest.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.persistence.models import Base
from app.main import create_app
from fastapi.testclient import TestClient

@pytest.fixture(scope="function")
def db_session():
    """Cria banco SQLite in-memory para cada teste."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture(scope="function")
def client(db_session):
    """TestClient FastAPI com banco de teste."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_ai_client():
    """Mock do cliente de IA para testes sem chamadas de rede."""
    class MockAIClient:
        async def analyze_screening(self, paper, protocol):
            return {
                "decisao": "Incluído",
                "criterios_inclusao": {},
                "criterios_exclusao": {},
                "justificativa": "Mock response",
                "confianca": 0.95,
            }
        async def test_connection(self):
            return True
    return MockAIClient()
```

### 11.2.2 Categorias de Testes

| Categoria | Diretório | Escopo | Exemplos |
|-----------|-----------|--------|----------|
| **Domain** | `test_domain/` | Entidades e value objects | Paper.with_decision(), normalização de título |
| **Services** | `test_services/` | Lógica de negócio | ScreeningService.screen_paper(), DedupService |
| **API** | `test_api/` | Endpoints HTTP | CRUD projects, triagem em lote |
| **Harvesters** | `test_harvesters/` | Coleta (com mocks HTTP) | BDTD, SciELO parsing |

### 11.2.3 Exemplo: Teste de Domínio

```python
# tests/test_domain/test_entities.py

from app.domain.entities import Paper, Decision

def test_paper_with_decision():
    paper = Paper(id="1", title="Test", decision=Decision.PENDING)
    updated = paper.with_decision(Decision.INCLUDED)

    assert updated.decision == Decision.INCLUDED
    assert paper.decision == Decision.PENDING  # imutabilidade

def test_paper_with_exclusion_criterion():
    paper = Paper(id="1", title="Test")
    updated = paper.with_criterion("Fora do escopo", True, is_exclusion=True)

    assert updated.exclusion_criteria["Fora do escopo"] is True
    assert "Fora do escopo" not in paper.exclusion_criteria
```

### 11.2.4 Exemplo: Teste de API

```python
# tests/test_api/test_projects.py

def test_create_project(client):
    response = client.post("/api/v1/projects", json={
        "title": "Revisão sobre IA na Saúde",
        "methodology": "PRISMA-P",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Revisão sobre IA na Saúde"
    assert "id" in data

def test_list_projects(client):
    # Criar 3 projetos
    for i in range(3):
        client.post("/api/v1/projects", json={
            "title": f"Projeto {i}",
            "methodology": "PRISMA-P",
        })

    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    assert len(response.json()) == 3
```

---

## 11.3 Testes Frontend (React)

### Framework: Vitest + React Testing Library

### 11.3.1 Configuração

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
});
```

### 11.3.2 Exemplo: Teste de Componente

```typescript
// components/domain/PaperCard.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { PaperCard } from './PaperCard';

const mockPaper = {
  id: '1',
  title: 'Machine Learning in Healthcare',
  authors: 'Silva, J.',
  year: '2024',
  source: 'SciELO',
  decision: 'Pendente',
  abstract: 'This study explores...',
};

describe('PaperCard', () => {
  it('renders paper title', () => {
    render(<PaperCard paper={mockPaper} />);
    expect(screen.getByText('Machine Learning in Healthcare')).toBeInTheDocument();
  });

  it('shows pending badge', () => {
    render(<PaperCard paper={mockPaper} />);
    expect(screen.getByText('Pendente')).toHaveClass('badge-pending');
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<PaperCard paper={mockPaper} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('article'));
    expect(onSelect).toHaveBeenCalledWith('1');
  });
});
```

---

## 11.4 Testes E2E (Electron)

### Framework: Playwright + Electron

```typescript
// e2e/app.spec.ts

import { test, expect, _electron as electron } from '@playwright/test';

test('app launches and shows dashboard', async () => {
  const app = await electron.launch({
    args: ['.'],
  });

  const window = await app.firstWindow();
  await window.waitForSelector('[data-testid="dashboard"]');

  const title = await window.title();
  expect(title).toContain('RSAC');

  await app.close();
});

test('can create a new project', async () => {
  const app = await electron.launch({ args: ['.'] });
  const window = await app.firstWindow();

  await window.click('[data-testid="new-project-button"]');
  await window.fill('[data-testid="project-title"]', 'Minha Revisão');
  await window.selectOption('[data-testid="methodology-select"]', 'PRISMA-P');
  await window.click('[data-testid="create-project-submit"]');

  await expect(window.locator('[data-testid="project-card"]')).toHaveCount(1);

  await app.close();
});
```

---

## 11.5 Linting e Formatação

### Python (Backend)

```toml
# pyproject.toml

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
```

### TypeScript (Frontend)

```json
// .eslintrc.cjs
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended"
  ],
  "rules": {
    "no-unused-vars": "error",
    "@typescript-eslint/no-explicit-any": "warn"
  }
}
```

---

## 11.6 CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
        working-directory: backend
      - run: uv run pytest --cov --cov-report=xml
        working-directory: backend
      - run: uv run ruff check .
        working-directory: backend
      - run: uv run mypy .
        working-directory: backend

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run test
        working-directory: frontend
      - run: npm run build
        working-directory: frontend

  e2e:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - uses: astral-sh/setup-uv@v5
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
        working-directory: frontend
```

---

## 11.7 Métricas de Qualidade

| Métrica | Meta |
|---------|------|
| Cobertura de testes (backend) | ≥ 80% |
| Cobertura de testes (frontend) | ≥ 70% |
| Testes E2E passando | 100% |
| Lint errors | 0 |
| Type errors (mypy) | 0 |
| Build sem warnings | ✅ |
