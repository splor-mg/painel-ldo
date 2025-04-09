# Ferramenta de Processamento de Dados do Painel LDO

Esta ferramenta processa dados financeiros, cria indicadores sobre a qualidade dos dados presentes e os disponibiliza para serem consumidos pelo painel-ldo ou outras ferramentas. A extração de dados é feita dos dados de execução financeira e orçamentária dos dois últimos anos (execucao), dados de reestimativa fiscal do ano corrente (reest), previsão inicial da Lei Orçamentária Anual do ano corrente e dados da Lei de Diretrizes Orçamentárias (LDO) lançados no Sistema Orçamentário (SISOR) do próximo exercício.

## Recursos

- Extração de dados usando a ferramenta DPM
- Processamento e análise de dados financeiros
- Geração de arquivos de saída estruturados para análise de receitas e fontes
- Transformação e processamento automatizado de dados

## Pré-requisitos

- Python 3.x
- Ferramenta DPM instalada e acessível no PATH ou num `virtualenv`

## Instalação

1. Clone este repositório:
   ```bash
   git clone [repository-url]
   cd painel-ldo
   ```

2. Instale as dependências Python:
   ```bash
   pip install -r requirements.txt
   ```

3. Certifique-se de que a ferramenta DPM esteja instalada e configurada corretamente no PATH do seu sistema

4. Siga as instruções do arquivo `data.toml` para configurar as variáveis de ambiente "token" para ter acesso aos reposiórios privados da SPLOR.

## Uso

A ferramenta fornece dois comandos principais:

### 1. Extrair Dados

Execute o processo de instalação do DPM:
```bash
python main.py extract
```

### 2. Construir Arquivos de Dados

Processe e analise os dados:
```bash
python main.py build
```

## Arquivos de Saída

A ferramenta gera os seguintes arquivos de saída no diretório `data`:

- `fonte_analise.csv` e `fonte_analise.xlsx`: Dados de análise de fontes
- `receita_analise.csv` e `receita_analise.xlsx`: Dados de análise de receitas

## Estrutura do Projeto

```
├── main.py              # Ponto de entrada principal da aplicação
├── databases.py         # Operações de banco de dados e processamento de dados
├── requirements.txt     # Dependências Python
├── data.toml           # Arquivo de configuração utilizado pelo dpm
├── README.md            # Este arquivo
├── template_painel.R    # Template R para o painel
└── data/               # Diretório de saída para arquivos processados
```

## Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para enviar um Pull Request.

## Licença

Este projeto está licenciado sob os termos da licença MIT.