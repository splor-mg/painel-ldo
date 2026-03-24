# Ferramenta de Processamento de Dados do Painel LDO

Esta ferramenta processa dados financeiros e indicadores sobre a qualidade dos dados presentes e os disponibiliza para serem consumidos pelo painel-ldo ou outras ferramentas.
A extração de dados é feita dos dados de execução financeira e orçamentária dos dois últimos anos (execucao), dados de reestimativa fiscal do ano corrente (reest), previsão inicial da Lei Orçamentária Anual do ano corrente e dados da Lei de Diretrizes Orçamentárias (LDO) lançados no Sistema Orçamentário (SISOR) do próximo exercício.

## Recursos

- Extração de dados usando a [ferramenta DPM](https://github.com/splor-mg/dpm).
- Processamento e análise de dados financeiros.
- Geração de arquivos de saída estruturados para análise de receitas e fontes.
- Transformação e processamento automatizado de dados.

## Pré-requisitos

- Python 3.x.
- Poetry.
- Ferramenta [dpm](https://github.com/splor-mg/dpm).
- Pacote [R relatórios](https://github.com/splor-mg/relatorios) instalado.
- Variaveis de ambiente `R_HOME` e `GH_TOKEN` configuradas no arquivo `.env`.

## Instalações R

Os comandos abaixo deverão ser executados apenas a primeira vez (durante o setup do repositório na máquina).

Antes de rodar os comandos é necessário ter variável de ambiente GH_TOKEN configurada corretamente no arquivo .env.
Para isso, gere um token (fine-granted) nas configurações de GitHub com todos os repositórios necessários para a atualização, tais como:

- [Pacote Relatório (R)](https://github.com/splor-mg/relatorios).
- [dados-armazem-siafi](https://github.com/orgs/splor-mg/repositories?q=dados-armazem-siafi) com o(s) ano(s) correspondente(s) às necessidades.
- [dados-reestimativa](https://github.com/orgs/splor-mg/repositories?q=dados-reestimativa) com o(s) ano(s) correspondente(s) às necessidades.
- dados-ppo (ainda manual).


```
export $(grep -v '^#' .env | xargs)
Rscript -e "dir.create('~/R', showWarnings = FALSE); .libPaths('~/R'); install.packages('remotes', repos='https://cloud.r-project.org')"
Rscript -e ".libPaths('~/R'); remotes::install_github('splor-mg/relatorios', auth_token = Sys.getenv('GH_TOKEN'))"
export R_LIBS_USER=~/R # Necessário para rodar os comandos task extract e task build
```

## Instalação Python

1. Clone este repositório:

```bash
git clone https://github.com/splor-mg/painel-ldo.git
cd painel-ldo
```

2. Instale as dependências Python:

```bash
poetry install
```

## Atualizando os dados

1. Crie o arquivo `data.toml`[^1]:

```bash
task toml
```

[^1]: Arquivo `data.toml` necessário para execução dos comandos `task extract` e `task build` deverá ser gerado dinamicamente via comando `task toml`.

2. Extraia os dados:

```bash
task extract
```

3. Atualize os arquivos de dados (pasta `data/`):

```bash
task build
```

4. Rode tudo de uma única vez

Se preferir rodar os comandos em sequência, substitua os comandos acima por:

```bash
task painel
```

## Arquivos de Saída

A ferramenta gera os seguintes arquivos de saída na pasta `data/`:

- `fonte_analise.csv` e `fonte_analise.xlsx`: Dados de análise de fontes.
- `receita_analise.csv` e `receita_analise.xlsx`: Dados de análise de receitas.
