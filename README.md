# Painel LDO — Observable Framework

Versão estática do Painel LDO construída com [Observable Framework](https://observablehq.com/framework/).

## Por que Observable Framework?

Neste README vou inserir algumas comparações entre ferramentas que estou realizando testes considerando algumas premissas. Sendo elas:

1. Open source;
2. Site estático;
3. Github Pages;
4. Filtros interativos;
5. Sem servidor;
6. Markdown nativo;
7. Integração com Python;
8. Gratuito.

## Estrutura do Projeto

```
painel-ldo-observable/
├── observablehq.config.js   # Configuração: título, páginas, sidebar
├── package.json
├── src/
│   ├── index.md             # Página: Visão Geral
│   ├── fonte-recursos.md    # Página: Fonte de Recursos
│   ├── ldo-2027.md          # Página: LDO 2027
│   └── data/
│       ├── receita.json     # Dados pré-processados
│       ├── fonte.json
│       └── ldo2027.json
```

## Como Rodar Localmente

```bash
# Instalar dependências
npm install

# Servidor de desenvolvimento com hot reload
npm run dev
# Acesse: http://localhost:3000

# Gerar build estático
npm run build
# Saída em: dist/
```

## Deploy no GitHub Pages

Adicione este workflow em `.github/workflows/deploy.yml`:

```yaml
name: Deploy to GitHub Pages
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run build
      - uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: dist
```

## Integração com Poetry (Pipeline de Dados)

O Observable Framework pode consumir dados gerados pelo pipeline Python existente.
Adicione um data loader em `src/data/receita.json.py`:

```python
# src/data/receita.json.py
# Este arquivo é executado pelo Observable antes do build
import sys
sys.path.insert(0, "../../")
from painel_ldo.databases import ...
import json
# gere o JSON e print para stdout
print(json.dumps(dados))
```

Ou simplesmente rode `task build` do Poetry antes do `npm run build`.

## Comparação de Ferramentas

### Base
| Critério        | Observable | Evidence | Marimo | Panel | Quarto | Streamlit |
|----------------|------------|----------|--------|-------|--------|-----------|
| Open source     | Sim        | Sim      | Sim    | Sim   | Sim    | Sim       |
| Gratuito        | Sim        | Sim      | Sim    | Sim   | Sim    | Sim       |

### Deploy e Infraestrutura
| Critério        | Observable | Evidence | Marimo | Panel | Quarto | Streamlit |
|----------------|------------|----------|--------|-------|--------|-----------|
| Site estático   | Sim        | Sim      | Sim    | Sim   | Sim    | Não       |
| GitHub Pages    | Sim        | Sim      | Sim    | Sim   | Sim    | Não       |
| Sem servidor    | Sim        | Sim      | Sim    | Sim   | Sim    | Não       |

### Desenvolvimento
| Critério                  | Observable | Evidence | Marimo | Panel | Quarto | Streamlit |
|--------------------------|------------|----------|--------|-------|--------|-----------|
| Markdown/Python nativo   | Sim        | Sim      | Sim    | Sim   | Sim    | Não       |
| Filtros interativos      | Alto       | Alto     | Alto   | Alto  | Médio  | Alto      |
| Python puro (sem JS)     | Médio      | Médio    | Alto   | Alto  | Médio  | Alto      |
| Integração Poetry        | Sim        | Médio    | Alto   | Sim   | Sim    | Sim       |

### Tecnologias
| Critério        | Observable | Evidence | Marimo | Panel | Quarto | Streamlit |
|----------------|------------|----------|--------|-------|--------|-----------|
| Pyodide/WASM<sup>1</sup>   | Não        | Não      | Sim    | Sim   | Médio  | Não       |

---

### Legenda

- **Sim**: suporte completo  
- **Não**: não suportado  
- **Médio**: suporte parcial / com limitações  
- **Alto**: suporte forte / bem integrado

##### 1. _Pyodide é uma distribuição do interpretador Python (CPython) compilada para WebAssembly (WASM)/Emscripten, permitindo executar código Python diretamente no navegador ou Node.js, sem servidor. Ele oferece alta interoperabilidade com JavaScript, acesso ao DOM e suporte a bibliotecas científicas como NumPy, Pandas e Matplotlib._