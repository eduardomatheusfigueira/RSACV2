# 🌐 Aula 04: Motores de Coleta e Harvesters Acadêmicos

> **Como o Revsist se conecta e recupera dezenas de milhares de artigos de bases científicas**

---

## 1. O Contrato de Coleta (`BaseHarvester`)

Cada base científica no mundo possui sua própria arquitetura de dados (REST, GraphQL, OAI-PMH, XML, JSON, etc.). Para uniformizar o tratamento desses dados, o sistema adota o padrão **Adapter/Strategy** através da classe abstrata `BaseHarvester` (`app/harvesters/base.py`):

```python
class BaseHarvester(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 100,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        **kwargs
    ) -> List[HarvestedPaper]:
        """Executa a busca na base externa e retorna uma lista padronizada de artigos."""
        pass
```

Dessa forma, a camada de serviços não precisa saber detalhes de implementação de nenhuma base específica. Ela apenas chama `search()` e recebe objetos uniformizados do tipo `HarvestedPaper` contendo:
- `title` (Título limpo)
- `abstract` (Resumo)
- `authors` (Lista de autores)
- `year` (Ano de publicação)
- `doi` (Identificador único DOI)
- `source_database` (Nome da base: "SciELO", "BDTD", "Scopus", etc.)
- `journal` / `publisher` (Nome da revista ou instituição)
- `url` (Link para o estudo original)

---

## 2. O Harvester SciELO (`scielo.py`)

A coleção **SciELO** (*Scientific Electronic Library Online*) é o maior repositório de literatura científica de acesso aberto da América Latina e do Sul Global.

### 💡 A Solução de Alta Disponibilidade via CrossRef API
Historicamente, buscas automatizadas diretamente no portal web da SciELO enfrentavam limitações de paginação e instabilidades de endpoint. Para garantir robustez e velocidade industrial, o Harvester SciELO do Revsist opera via **CrossRef REST API** com filtragem de prefixos de DOI pertencentes à SciELO (como `10.1590`, `10.11606`, etc.):

1. **Construção da Query:** O coletor converte os descritores de busca do protocolo no parâmetro `query.bibliographic`.
2. **Filtro Temporal:** Aplica restrições de data precisas (`from-pub-date` e `until-pub-date`).
3. **Paginação em Lote:** Faz paginação inteligente via `offset` e `rows` (com lotes de até 100 artigos por requisição).
4. **Sanitização de Metadados:** Limpa tags XML/HTML de resumos e títulos usando expressões regulares e decodificação UTF-8.

---

## 3. O Harvester BDTD (`bdtd.py`)

A **BDTD** (*Biblioteca Digital Brasileira de Teses e Dissertações*, mantida pelo IBICT) reúne a produção acadêmica de mestrado e doutorado de centenas de universidades brasileiras.

### ⚠️ A Regra Metodológica de Ouro: Estrutura em Pares
O motor de busca da BDTD é baseado na tecnologia **VuFind**. Expressões booleanas muito longas com múltiplos `AND` aninhados (ex: `"termo_1" AND "termo_2" AND "termo_3" AND "termo_4"`) causam sobrecarga de indexação e retornam falso zero ou erro HTTP 500 no VuFind.

Por essa razão, o protocolo de busca do Revsist segue a diretriz:
- **Descritores em Pares:** Máximo de 2 termos por expressão (ex: `"mobilidade turistica" AND "desenvolvimento regional"`).
- **Limite por Idioma:** Até 5 pares de termos por idioma (Português, Inglês, Espanhol).

---

## 4. Outros Harvesters Suportados

- **Scopus (`scopus.py`):** Consulta a API oficial da Elsevier usando chaves institucionais do pesquisador (`X-ELS-APIKey`), permitindo recuperação detalhada de citações e abstracts.
- **PubMed (`pubmed.py`):** Conecta-se aos utilitários E-utilities da *National Library of Medicine* (NCBI) via `esearch` e `efetch`.
- **IEEE Xplore (`ieee.py`):** Acessa a API da IEEE para busca em congressos e periódicos de engenharia e computação.

---

## 5. Prevenção de Falsos Zeros e Persistência Resiliente

Em versões legadas de ferramentas de busca, uma falha na internet no artigo número 999 fazia todo o lote de 1.000 artigos ser descartado.

No Revsist:
1. **Gravação Incremental (`_persist_batch_sync`):** A cada 25 artigos recuperados de qualquer base, uma transação atômica grava os registros no banco de dados SQLite/Postgres.
2. **Atualização Imediata das Métricas:** Os contadores `records_found`, `records_new` e `records_duplicate` no registro da coleta (`HarvestRunModel`) são persistidos a cada lote.
3. **Feedback ao Vivo no Frontend:** O polling (`/api/v1/harvest/status`) lê o banco e atualiza imediatamente os contadores visuais na tela do usuário, garantindo que o progresso nunca fique congelado em zero.

---

Na próxima aula, vamos explorar o cérebro da aplicação:  
👉 **[Aula 05: Motor de Inteligência Artificial e Triagem](./05_MOTOR_DE_IA_E_TRIAGEM.md)**
