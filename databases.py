import pandas as pd
import numpy as np
from datetime import datetime, date
import os
from pathlib import Path
from R_runner import is_convenios_rec, is_intra_saude_rec, adiciona_desc
import openpyxl
import warnings
import dotenv
warnings.filterwarnings('ignore')

dotenv.load_dotenv()

# Custom package imports - these need to be properly implemented
# from execucao import valor_painel, loa_rec  # TODO: Implement these custom package equivalents
# from relatorios import add_de_para_receita  # TODO: Implement this custom package equivalent

# CONFIGURATIONS
ANO_REF = datetime.now().year
ANO_REF_LDO = ANO_REF + 1
DATA = date.today()


# PARAMETERS
fontes_convenios = list(range(1, 10)) + [16, 17, 24, 36, 37, 56, 57] + \
                   list(range(62, 71)) + [73, 74, 92, 93, 97, 98]


# BASE EXECUCAO


# Equivalent columns for LDO files

def carrega_trata_dados():

    columns_to_use = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'receita_desc', 'receita_cod_formatado', 'vlr_previsto_inicial', 'vlr_efetivado_ajustado']

    valor_painel2023 = pd.read_csv("datapackages/execucao2023/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
    valor_painel2024 = pd.read_csv("datapackages/execucao2024/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
    valor_painel2025 = pd.read_csv("datapackages/execucao2025/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
    valor_painel2025['ano'] = '2025_loa'

    valor_painel_concat = pd.concat([valor_painel2023, valor_painel2024, valor_painel2025], ignore_index=True)

    columns_to_use_ldo = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'vlr_loa_rec']
    ldo_2026 = pd.read_csv("datapackages/sisor2026/data/base_orcam_receita_fiscal.csv", usecols=columns_to_use_ldo)

    columns_to_use_reestimativa = [ 'ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'vlr_reest_rec']
    valor_painel2025_reestimativa = pd.read_csv("datapackages/reestimativa2025/data/reest_rec.csv", usecols=columns_to_use_reestimativa)
    valor_painel2025_reestimativa['ano'] = '2025_reest'

    # Get all columns from both dataframes
    all_columns = list(set(valor_painel_concat.columns) | set(ldo_2026.columns) | set(valor_painel2025_reestimativa.columns))

    # Add missing columns to each dataframe with NaN values
    for col in all_columns:
        if col not in valor_painel_concat.columns:
            valor_painel_concat[col] = np.nan
        if col not in ldo_2026.columns:
            ldo_2026[col] = np.nan
        if col not in valor_painel2025_reestimativa.columns:
            valor_painel2025_reestimativa[col] = np.nan

    # Concatenate the dataframes keeping both value columns
    valor_painel = pd.concat([valor_painel_concat, ldo_2026, valor_painel2025_reestimativa], ignore_index=True)
    valor_painel.rename(columns={'vlr_loa_rec': 'vlr_ldo', 'vlr_reest_rec': 'vlr_reest'}, inplace=True)

    # Ajusta o valor painel para o ano de 2025
    valor_painel['valor_painel'] = np.where(
        valor_painel['ano'].isin([ANO_REF_LDO-4, ANO_REF_LDO-3, ANO_REF_LDO-2]),
        valor_painel['vlr_efetivado_ajustado'], 
        np.where(valor_painel['ano'] == '2025_loa', valor_painel['vlr_previsto_inicial'], 
            np.where(valor_painel['ano'] == '2025_reest', valor_painel['vlr_reest'],
                valor_painel['vlr_ldo']
            )
        )
    )

    if not valor_painel.empty:
        valor_painel['uo_cod'] = np.where(valor_painel['uo_cod'] == 9999, 9901, valor_painel['uo_cod'])
        return valor_painel

    else:
        print("Dataframe valor_painel carregado não possui dados.\n")
        exit(1)


def cria_base_receita_analise(valor_painel):

    # TRATAMENTO DAS BASES
    # BASE CONVENIOS
    base_convenios = valor_painel[valor_painel['fonte_cod'].isin(fontes_convenios)]
    base_convenios = base_convenios.groupby(['ano', 'uo_cod', 'fonte_cod'])['valor_painel'].sum().reset_index()

    # BASE DEMAIS FONTES
    base_demais = valor_painel[~valor_painel['fonte_cod'].isin(fontes_convenios)]
    base_demais = base_demais.groupby(['ano', 'uo_cod', 'receita_cod', 'fonte_cod'])['valor_painel'].sum().reset_index()

    base_convenios = base_convenios.astype({'uo_cod': pd.Int64Dtype(), 'fonte_cod': pd.Int64Dtype(),})
    base_demais = base_demais.astype({'uo_cod': pd.Int64Dtype(), 'fonte_cod': pd.Int64Dtype(), 'receita_cod': pd.StringDtype()})

    # BASE ANALISE
    base_analise = pd.concat([base_convenios, base_demais], ignore_index=True)
    base_analise['receita_cod'] = base_analise['receita_cod'].fillna('-')
    base_analise = base_analise[['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'valor_painel']]

    base_analise = base_analise.groupby(['ano', 'uo_cod', 'receita_cod', 'fonte_cod']).sum().reset_index()

    # Pivot the table
    base_analise = base_analise.pivot_table(
        index=['uo_cod', 'receita_cod', 'fonte_cod'],
        columns='ano',
        values='valor_painel',
        aggfunc='sum'
    ).reset_index()

    # Fill NaN values with 0 and round to 2 decimal places
    numeric_columns = base_analise.select_dtypes(include=[np.number]).columns
    numeric_columns = numeric_columns.drop(['uo_cod', 'fonte_cod'])

    base_analise[numeric_columns] = base_analise[numeric_columns].fillna(0).round(2)
    # Reorder columns based on specific order
    column_order = ['uo_cod', 'receita_cod', 'fonte_cod', ANO_REF_LDO-3, ANO_REF_LDO-2, f"{ANO_REF_LDO-1}_reest", f"{ANO_REF_LDO-1}_loa", ANO_REF_LDO]
    base_analise = base_analise[column_order]



    # ALERTAS
    base_analise.loc[:, 'ano'] = ANO_REF


    base_analise['CONVENIOS'] = is_convenios_rec(base_analise)
    base_analise['INTRA_SAUDE'] = is_intra_saude_rec(base_analise)


    # Create ALERTAS column with conditions
    conditions = [
        (base_analise['INTRA_SAUDE'] == True),
        (base_analise['fonte_cod'].isin(fontes_convenios)),
        ((base_analise['CONVENIOS'] == True) & ~base_analise['fonte_cod'].isin(fontes_convenios)),
        ((base_analise.iloc[:, 3] > 0) & 
        (base_analise.iloc[:, 4] > 0) & 
        (base_analise.iloc[:, 5] > 0) & 
        (base_analise.iloc[:, 7] == 0)),
        (((base_analise.iloc[:, 4] > 0) & (base_analise.iloc[:, 7] == 0)) |
        ((base_analise.iloc[:, 5] > 0) & (base_analise.iloc[:, 7] == 0))),
        (
            (base_analise.iloc[:, 7] > 0) &
            ((base_analise.iloc[:, 3:6].sum(axis=1) / 3) > 0) &
            (
                (
                    (base_analise.iloc[:, 7] > ((base_analise.iloc[:, 3:6].sum(axis=1) / 3) * 2)) &
                    (base_analise.iloc[:, 7] > (1.2 * base_analise.iloc[:, 3:6].max(axis=1)))
                ) |
                (
                    (base_analise.iloc[:, 7] < (base_analise.iloc[:, 3:6].sum(axis=1) / 3 / 2)) &
                    (base_analise.iloc[:, 7] < (0.9 * base_analise.iloc[:, 3:6].min(axis=1)))
                )
            )
        )
    ]

    choices = [
        "Receita de repasse do FES é lançada pela SPLOR",
        "Receita a ser informada pela DCGCE/SEPLAG",
        "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA",
        "RECEITA NAO ESTIMADA",
        "ATENCAO",
        "VALOR DISCREPANTE"
    ]

    base_analise['ALERTAS'] = np.select(conditions, choices, default="OK")

    # Adiciona descrições
    base_analise['ano'] = ANO_REF
    base_analise = adiciona_desc(base_analise, ['RECEITA_COD', 'UO_COD', 'FONTE_COD'], overwrite=True)
    base_analise.columns = base_analise.columns.str.lower()

    # Remove colunas não necessárias
    base_analise = base_analise.drop(['ano', 'intra_saude', 'convenios'], axis=1)
    
    
    # Verificar se é necessário filtrar
    base_analise = base_analise[
        ~((base_analise['uo_cod'] == 4461) | (base_analise['fonte_cod'] == 58))
    ] 

    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    base_analise.to_csv("data/receita_analise.csv", index=False)
    base_analise.to_excel("data/receita_analise.xlsx", index=False)

def cria_base_fonte_analise(valor_painel):

    # TRATAMENTO DAS BASES
    # BASE CONVENIOS

    base_fonte_agg = valor_painel.groupby(['ano', 'uo_cod', 'fonte_cod'])['valor_painel'].sum().reset_index()

        # Pivot the table
    base_fonte_agg = base_fonte_agg.pivot_table(
        index=['uo_cod', 'fonte_cod'],
        columns='ano',
        values='valor_painel',
        aggfunc='sum'
    ).reset_index()

    # Fill NaN values with 0 and round to 2 decimal places
    numeric_columns = base_fonte_agg.select_dtypes(include=[np.number]).columns
    numeric_columns = numeric_columns.drop(['uo_cod', 'fonte_cod'])

    base_fonte_agg[numeric_columns] = base_fonte_agg[numeric_columns].fillna(0).round(2)
    # Reorder columns based on specific order
    column_order = ['uo_cod', 'fonte_cod', ANO_REF_LDO-3, ANO_REF_LDO-2, f"{ANO_REF_LDO-1}_reest", f"{ANO_REF_LDO-1}_loa", ANO_REF_LDO]
    base_fonte_agg = base_fonte_agg[column_order]


        # ALERTAS
    base_fonte_agg.loc[:, 'ano'] = ANO_REF
    #base_fonte_agg['CONVENIOS'] = is_convenios_rec(base_fonte_agg)
    #base_fonte_agg['INTRA_SAUDE'] = is_intra_saude_rec(base_fonte_agg)


    # Create ALERTAS column with conditions
    conditions = [
        #(base_fonte_agg['INTRA_SAUDE'] == True),
        #(base_fonte_agg['fonte_cod'].isin(fontes_convenios)),
        #((base_fonte_agg['CONVENIOS'] == True) & ~base_fonte_agg['fonte_cod'].isin(fontes_convenios)),
        ((base_fonte_agg.iloc[:, 3] > 0) & 
        (base_fonte_agg.iloc[:, 4] > 0) & 
        (base_fonte_agg.iloc[:, 5] > 0) & 
        (base_fonte_agg.iloc[:, 7] == 0)),
        (((base_fonte_agg.iloc[:, 4] > 0) & (base_fonte_agg.iloc[:, 7] == 0)) |
        ((base_fonte_agg.iloc[:, 5] > 0) & (base_fonte_agg.iloc[:, 7] == 0))),
        (
            (base_fonte_agg.iloc[:, 7] > 0) &
            ((base_fonte_agg.iloc[:, 3:6].sum(axis=1) / 3) > 0) &
            (
                (
                    (base_fonte_agg.iloc[:, 7] > ((base_fonte_agg.iloc[:, 3:6].sum(axis=1) / 3) * 2)) &
                    (base_fonte_agg.iloc[:, 7] > (1.2 * base_fonte_agg.iloc[:, 3:6].max(axis=1)))
                ) |
                (
                    (base_fonte_agg.iloc[:, 7] < (base_fonte_agg.iloc[:, 3:6].sum(axis=1) / 3 / 2)) &
                    (base_fonte_agg.iloc[:, 7] < (0.9 * base_fonte_agg.iloc[:, 3:6].min(axis=1)))
                )
            )
        )
    ]

    choices = [
        #"Receita de repasse do FES é lançada pela SPLOR",
        #"Receita a ser informada pela DCGCE/SEPLAG",
        #"RECEITA DE CONVENIOS EM FONTE NAO ESPERADA",
        "RECEITA NAO ESTIMADA",
        "ATENCAO",
        "VALOR DISCREPANTE"
    ]

    base_fonte_agg['ALERTAS'] = np.select(conditions, choices, default="OK")

    # Adiciona descrições
    base_fonte_agg['ano'] = ANO_REF
    base_fonte_agg = adiciona_desc(base_fonte_agg, ['UO_COD', 'FONTE_COD'], overwrite=True)
    base_fonte_agg.columns = base_fonte_agg.columns.str.lower()

    # Remove colunas não necessárias
    base_fonte_agg = base_fonte_agg.drop(['ano'], axis=1)
    
    
    # Verificar se é necessário filtrar
    #base_fonte_agg = base_fonte_agg[
    #    ~((base_fonte_agg['uo_cod'] == 4461) | (base_fonte_agg['fonte_cod'] == 58))
    #] 


    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    base_fonte_agg.to_csv("data/fonte_analise.csv", index=False)
    base_fonte_agg.to_excel("data/fonte_analise.xlsx", index=False)





