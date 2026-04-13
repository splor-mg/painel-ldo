from R_runner import is_convenios_rec, is_intra_saude_rec, adiciona_desc
from frictionless import Package
import tomli_w
import pandas as pd
import numpy as np
import os
import openpyxl
import warnings
from datetime import datetime, date
from pathlib import Path
warnings.filterwarnings('ignore')


# Custom package imports - these need to be properly implemented
# from execucao import valor_painel, loa_rec  # TODO: Implement these custom package equivalents
# from relatorios import add_de_para_receita  # TODO: Implement this custom package equivalent

# CONFIGURATIONS
# TODO: TRAZER DESCRIÇÃO DA FONTE DAS TABELAS AUXILIARES
ANO_REF = datetime.now().year  # Year when the analysis will be based on.
ANO_REF_LDO = ANO_REF + 1
DATA = date.today()


# PARAMETERS
# TODO: LAURA revisa as fontes de convenio
# convenios tem que ser arrecadados em fontes de
fontes_convenios = list(range(1, 10)) + [16, 17, 24, 36, 37, 56, 57] + \
    list(range(62, 71)) + [73, 74, 92, 93, 97, 98]


def build_toml():
    config = {"packages": {}}

    for year in range(ANO_REF - 3, ANO_REF + 1):
        config["packages"][f"siafi_{year}"] = {
            "path": f"https://raw.githubusercontent.com/splor-mg/dados-armazem-siafi-{year}/main/datapackage.json",
            "token": "GH_TOKEN",
            "resources": ["receita"],
        }
        if year == ANO_REF:
            config["packages"][f"reestimativa_{year}"] = {
                "path": f"https://raw.githubusercontent.com/splor-mg/dados-reestimativa-{year}/main/datapackage.json",
                "token": "GH_TOKEN",
                "resources": ["reest_rec"],
            }
        # TODO: Add ppo datapackage when it was available in dados-ppo repository

    config["packages"]["dados-aux-classificadores"] = {
        "path": "https://raw.githubusercontent.com/splor-mg/dados-aux-classificadores/main/datapackage.json",
        "token": "GH_TOKEN",
        "resources": ["uo", "fonte_recurso"],
    }

    with open("data.toml", "wb") as f:
        tomli_w.dump(config, f)


def build_df(datapackage, columns_to_use):
    # TODO: Build datapackage folders name without years because every year we'll have to change the code.
    package = Package(f'datapackages/{datapackage}/datapackage.json')
    resource = package.get_resource(package.resource_names[0])
    df = resource.to_pandas()
    df = df[columns_to_use]
    if datapackage.endswith(str(ANO_REF)):
        df['ano'] = datapackage
    return df


def carrega_trata_dados():

    # Load, filter columns and concatenate siafi data
    siafi_columns_to_use = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'receita_cod_formatado',
                            # vlr_previsto_inicial LOA, vlr_efetivado_ajustado o que arrecadou
                            'vlr_previsto_inicial', 'vlr_efetivado_ajustado']

    siafi_dfs = []
    # (ANO_REF, ANO_REF -1, ANO_REF -2, ANO_REF -3)
    for year in range(ANO_REF, ANO_REF - 4, -1):
        siafi_df = build_df(f'siafi_{year}', siafi_columns_to_use)
        siafi_dfs.append(siafi_df)
    siafi_df = pd.concat(siafi_dfs, ignore_index=True)

    # Load and filter columns reestimativa data
    reestimativa_columns_to_use = ['ano', 'uo_cod',
                                   'receita_cod', 'fonte_cod', 'vlr_reest_rec']
    reestimativa_df = build_df(
        f'reestimativa_{ANO_REF}', reestimativa_columns_to_use)

    # Load and filter columns ppo data
    # TODO: When ppo data come from dados-ppo call fields name snake_small_case
    ppo_columns_to_use = ['Ano', 'Código da Unidade',
                          'Classificação da Receita', 'Fonte', 'Valor LDO']
    ppo_df = build_df(f'ppo_{ANO_REF_LDO}', ppo_columns_to_use)
    ppo_df.rename(columns={'Ano': 'ano',
                           'Código da Unidade': 'uo_cod',
                           'Classificação da Receita': 'receita_cod',
                           'Fonte': 'fonte_cod',
                           'Valor LDO': 'vlr_loa_rec'
                           }, inplace=True)
    ppo_df['receita_cod'] = (
        ppo_df['receita_cod']
        .str.replace('.', '', regex=False)
        .astype('Int64')  # nullable integer type
    )  # Remove dots from receita_cod to match siafi format

    # Get all columns from both dataframes
    all_columns = list(set(siafi_columns_to_use) |
                       set(reestimativa_columns_to_use) |
                       # TODO: When ppo data come from dados-ppo call fields name snake_small_case
                       # Here ppo_df.columns will turn to just ppo_columns_to_use
                       set(ppo_df.columns)
                       )

    # Add missing columns to each dataframe with NaN values
    for col in all_columns:
        if col not in siafi_columns_to_use:
            siafi_df[col] = np.nan
        if col not in reestimativa_columns_to_use:
            reestimativa_df[col] = np.nan
        # TODO: When ppo data come from dados-ppo call fields name snake_small_case
        # Here ppo_df.columns will turn to just ppo_columns_to_use
        if col not in ppo_df.columns:
            ppo_df[col] = np.nan

    # Concatenate the dataframes keeping both value columns
    valor_painel = pd.concat(
        [siafi_df, reestimativa_df, ppo_df], ignore_index=True)
    # Valor LDO == vlor_loa_rec
    valor_painel.rename(
        columns={'vlr_loa_rec': 'vlr_ldo', 'vlr_reest_rec': 'vlr_reest'}, inplace=True)

    # Ajusta o valor painel para o ano de 2025
    valor_painel['valor_painel'] = np.where(
        valor_painel['ano'].isin([ANO_REF_LDO-4, ANO_REF_LDO-3, ANO_REF_LDO-2]),
        valor_painel['vlr_efetivado_ajustado'],
        np.where(
            valor_painel['ano'] == ANO_REF_LDO,
            valor_painel['vlr_ldo'],
            np.where(
                valor_painel['ano'].str.startswith('siafi'),
                valor_painel['vlr_previsto_inicial'],
                np.where(
                    valor_painel['ano'].str.startswith('reestimativa'),
                    valor_painel['vlr_reest'],
                    np.nan
                )
            )
        )
    )

    if not valor_painel.empty:
        # armazem 9999 é igual 9901 RGE Receita geral do estado
        valor_painel['uo_cod'] = np.where(
            valor_painel['uo_cod'] == 9999, 9901, valor_painel['uo_cod'])
        return valor_painel

    else:
        print("Dataframe valor_painel carregado não possui dados.\n")
        exit(1)



def cria_base_receita_fonte_analise(valor_painel, tipo_base):

    if tipo_base == 'receita':
        groupColumns = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod']
        nomeArquivo = 'data/receita_analise.csv'
    elif tipo_base == 'fonte':
        groupColumns = ['ano', 'uo_cod', 'fonte_cod']
        nomeArquivo = 'data/fonte_analise.csv'
    else:
        raise ValueError("A base deve ser do tipo 'receita' ou 'fonte'.")

    # TRATAMENTO DAS BASES
    # BASE CONVENIOS
    base_convenios = valor_painel[valor_painel['fonte_cod'].isin(
        fontes_convenios)]
    base_convenios = base_convenios.groupby(['ano', 'uo_cod', 'fonte_cod'])[
        'valor_painel'].sum().reset_index()

    # BASE DEMAIS FONTES
    base_demais = valor_painel[~valor_painel['fonte_cod'].isin(
        fontes_convenios)]
    base_demais = base_demais.groupby(groupColumns)[
        'valor_painel'].sum().reset_index()
    
    
    base_convenios = base_convenios.astype(
        {'uo_cod': pd.Int64Dtype(), 'fonte_cod': pd.Int64Dtype(), })
    base_demais = base_demais.astype({'uo_cod': pd.Int64Dtype(), 'fonte_cod': pd.Int64Dtype()})

    if 'receita_cod' in base_demais.columns:
        base_demais = base_demais.astype({ 'receita_cod': pd.StringDtype()})
        base_demais['receita_cod'] = base_demais['receita_cod'].fillna('-')
    
    # BASE ANALISE
    base_analise = pd.concat([base_convenios, base_demais], ignore_index=True)
    filterColumns = groupColumns.copy() + ['valor_painel']
    base_analise = base_analise[filterColumns]
    base_analise = base_analise.groupby(groupColumns).sum().reset_index()

    # Pivot the table
    pivotColumns = [col for col in groupColumns if col != 'ano']
    base_analise = base_analise.pivot_table(
        index=pivotColumns,
        columns='ano',
        values='valor_painel',
        aggfunc='sum'
    ).reset_index()

    # Fill NaN values with 0 and round to 2 decimal places
    numeric_columns = base_analise.select_dtypes(include=[np.number]).columns
    numeric_columns = numeric_columns.drop(['uo_cod', 'fonte_cod'])
    base_analise[numeric_columns] = base_analise[numeric_columns].fillna(
        0).round(2)
    
    # Reorder columns based on specific order
    if 'receita_cod' in base_analise.columns:
        columnOrder = ['uo_cod', 'receita_cod', 'fonte_cod', ANO_REF - 3, ANO_REF -
                        2, ANO_REF - 1, f"reestimativa_{ANO_REF}", f"siafi_{ANO_REF}", ANO_REF_LDO]
    else:
        columnOrder = ['uo_cod', 'fonte_cod', ANO_REF - 3, ANO_REF - 2,
                    ANO_REF - 1, f"reestimativa_{ANO_REF}", f"siafi_{ANO_REF}", ANO_REF_LDO]
    
    base_analise = base_analise[column_order]


    # ALERTAS
    base_analise.loc[:, 'ano'] = ANO_REF

    # Parametros iniciais
    cols_passado = [ANO_REF - 3, ANO_REF - 2, ANO_REF - 1]
    media_passado = base_analise[cols_passado].sum(axis=1) / 3
    max_passado = base_analise[cols_passado].max(axis=1)
    min_passado = base_analise[cols_passado].min(axis=1)

    if tipo_base == 'receita':
        base_analise['CONVENIOS'] = is_convenios_rec(base_analise)
        base_analise['INTRA_SAUDE'] = is_intra_saude_rec(base_analise)

    # Dicionário de regras
    
    regras_alertas = [

        # ===== ALERTAS SÓ RECEITA =====
        {
            "condicao": lambda df: df['INTRA_SAUDE'] == True,
            "alerta": "RECEITA REPASSE FES (LANÇAMENTO SPLOR)",
            "aplica_em": ["receita"]
        },
        {
            "condicao": lambda df: df['fonte_cod'].isin(fontes_convenios),
            "alerta": "RECEITA INFORMADA PELA DCGCE/SEPLAG",
            "aplica_em": ["receita"]
        },
        {
            "condicao": lambda df: (df['CONVENIOS'] == True) & ~df['fonte_cod'].isin(fontes_convenios),
            "alerta": "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA",
            "aplica_em": ["receita"]
        },

        # ===== ALERTAS COMUNS =====
        {
            "condicao": lambda df: (
                (df[ANO_REF - 3] > 0) &
                (df[ANO_REF - 2] > 0) &
                (df[ANO_REF - 1] > 0) &
                (df[ANO_REF_LDO] == 0)
            ),
            "alerta": "RECEITA NAO ESTIMADA",
            "aplica_em": ["receita", "fonte"]
        },
        {
            "condicao": lambda df: (
                ((df[ANO_REF - 2] > 0) & (df[ANO_REF_LDO] == 0)) |
                ((df[ANO_REF - 1] > 0) & (df[ANO_REF_LDO] == 0))
            ),
            "alerta": "ATENCAO",
            "aplica_em": ["receita", "fonte"]
        },
        {
            "condicao": lambda df: (
                (df[ANO_REF_LDO] > 0) &
                (media_passado > 0) &
                (
                    (
                        (df[ANO_REF_LDO] > (media_passado * 2)) &
                        (df[ANO_REF_LDO] > (1.2 * max_passado))
                    ) |
                    (
                        (df[ANO_REF_LDO] < (media_passado / 2)) &
                        (df[ANO_REF_LDO] < (0.9 * min_passado))
                    )
                )
            ),
            "alerta": "VALOR DISCREPANTE",
            "aplica_em": ["receita", "fonte"]
        }
    ]
    
    conditions = []
    choices = []

    for regra in regras_alertas:
        if tipo_base in regra["aplica_em"]:
            conditions.append(regra["cond"](base_analise))
            choices.append(regra["label"])
    
    base_analise['ALERTAS'] = np.select(conditions, choices, default="OK")

   
    # Adiciona descrições e remove colunas desnecessárias
    base_analise['ano'] = ANO_REF

    if tipo_base == 'receita':
        base_analise = adiciona_desc(base_analise, ['RECEITA_COD', 'UO_COD', 'FONTE_COD'], overwrite=True)
        base_analise = base_analise.drop(['ano', 'intra_saude', 'convenios'], axis=1)
        # Retira critérios que podem gerar alertas por não serem mais executados
        base_analise = base_analise[~((base_analise['uo_cod'] == 4461) | (base_analise['fonte_cod'] == 58))
    ]
    else:
        base_analise = adiciona_desc(base_analise, ['UO_COD', 'FONTE_COD'], overwrite=True)
        base_analise = base_analise.drop(['ano'], axis=1)
    

    base_analise.columns = base_analise.columns.str.lower()
    base_analise.insert(0, 'ano_ref', ANO_REF_LDO)

    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    base_analise.to_csv(nomeArquivo, index=False)

