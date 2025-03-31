import pandas as pd
import numpy as np
from datetime import datetime, date
import os
from pathlib import Path
import openpyxl
import warnings
warnings.filterwarnings('ignore')

# Custom package imports - these need to be properly implemented
# from execucao import exec_rec, loa_rec  # TODO: Implement these custom package equivalents
# from relatorios import add_de_para_receita  # TODO: Implement this custom package equivalent

# CONFIGURATIONS
CURRENT_DIR = Path(__file__).parent
os.chdir(CURRENT_DIR)
ANO_REF = datetime.now().year
ANO_REF_LDO = ANO_REF + 1
DATA = date.today()
OPERADOR = "Rodolfo"

# PARAMETERS
fontes_convenios = list(range(1, 10)) + [16, 17, 24, 36, 37, 56, 57] + \
                   list(range(62, 71)) + [73, 74, 92, 93, 97, 98]

def is_intra_saude_rec(df):
    # TODO: Implement this function based on your business logic
    return pd.Series([False] * len(df))

def is_convenios_rec(df):
    # TODO: Implement this function based on your business logic
    return pd.Series([False] * len(df))

def adiciona_desc(df, columns, overwrite=True):
    # TODO: Implement this function based on your business logic
    return df

# BASE EXECUCAO
# TODO: Replace with proper data loading once custom packages are implemented
# For now, we'll create placeholder DataFrames
columns_to_use = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'receita_desc', 'receita_cod_formatado', 'vlr_previsto_inicial', 'vlr_efetivado_ajustado']

# Equivalent columns for LDO files


exec_rec2022 = pd.read_csv("datapackages/execucao2022/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
exec_rec2023 = pd.read_csv("datapackages/execucao2023/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
exec_rec2024 = pd.read_csv("datapackages/execucao2024/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)
exec_rec2025 = pd.read_csv("datapackages/execucao2025/data/receita.csv.gz", compression='gzip', usecols=columns_to_use)


columns_to_use_ldo = ['ano', 'uo_cod', 'receita_cod', 'fonte_cod', 'receita_desc', 'vlr_loa_rec']
exec_rec_concat = pd.concat([exec_rec2022, exec_rec2023, exec_rec2024, exec_rec2025], ignore_index=True)

ldo_2026 = pd.read_csv("datapackages/sisor2026/data/base_orcam_receita_fiscal.csv", usecols=columns_to_use_ldo)

# Get all columns from both dataframes
all_columns = list(set(exec_rec_concat.columns) | set(ldo_2026.columns))

# Add missing columns to each dataframe with NaN values
for col in all_columns:
    if col not in exec_rec_concat.columns:
        exec_rec_concat[col] = np.nan
    if col not in ldo_2026.columns:
        ldo_2026[col] = np.nan

# Concatenate the dataframes keeping both value columns
exec_rec = pd.concat([exec_rec_concat, ldo_2026], ignore_index=True)
exec_rec.rename(columns={'vlr_loa_rec': 'vlr_ldo'}, inplace=True)


exec_rec['regra'] = np.where(
    exec_rec['ano'].isin([ANO_REF_LDO-4, ANO_REF_LDO-3, ANO_REF_LDO-2]),
    exec_rec['vlr_efetivado_ajustado'], 
    np.where(exec_rec['ano'] == ANO_REF_LDO-1, exec_rec['vlr_previsto_inicial'], 
    exec_rec['vlr_ldo']
    )
)


if not exec_rec.empty:
    exec_rec = exec_rec[exec_rec['ANO'] >= ANO_REF - 3].copy()
    exec_rec['VL_REC'] = exec_rec['VL_EFET_AJUST']
    exec_rec['UO_COD'] = np.where(exec_rec['UO_COD'] == 9999, 9901, exec_rec['UO_COD'])
    # TODO: Implement add_de_para_receita function
    # exec_rec = add_de_para_receita(exec_rec)
    exec_rec['RECEITA_COD'] = np.where(
        (exec_rec['ANO'] >= 2023) | exec_rec['RECEITA_COD_2'].isna(),
        exec_rec['RECEITA_COD'].astype(str),
        exec_rec['RECEITA_COD_2'].astype(str)
    )

# BASE LDO
try:
    ldo_sisor = pd.read_excel(f"../!bases/sisor/BASE_ORCAM_RECEITA_FISCAL_{DATA}.xlsx")
    ldo_sisor['VL_REC'] = ldo_sisor['VALOR FINAL (R$)']
    ldo_sisor['RECEITA_COD'] = ldo_sisor['COD_RECEITA'].astype(str)
    ldo_sisor['FONTE_COD'] = ldo_sisor['COD_FONTE']
except FileNotFoundError:
    print(f"Warning: LDO SISOR file not found for date {DATA}")
    ldo_sisor = pd.DataFrame()

try:
    ldo_rec = pd.read_excel("../!bases/ldo_rec.xlsx")
    ldo_rec['RECEITA_COD'] = ldo_rec['RECEITA_COD'].astype(str)
except FileNotFoundError:
    print("Warning: ldo_rec.xlsx file not found")
    ldo_rec = pd.DataFrame()

# BASE LOA
# TODO: Replace with proper data loading once custom packages are implemented
loa = pd.DataFrame()  # This should come from execucao.loa_rec
if not loa.empty:
    loa = loa[loa['ANO'] == ANO_REF].copy()
    loa['VL_REC'] = loa['VL_LOA_REC']

# BASE RECEITA
base_rec = pd.concat([exec_rec, loa, ldo_sisor], ignore_index=True)

# TRATAMENTO DAS BASES
# BASE CONVENIOS
base_convenios = base_rec[base_rec['FONTE_COD'].isin(fontes_convenios)]
base_convenios = base_convenios.groupby(['ANO', 'UO_COD', 'FONTE_COD'])['VL_REC'].sum().reset_index()

# BASE DEMAIS FONTES
base_demais = base_rec[~base_rec['FONTE_COD'].isin(fontes_convenios)]
base_demais = base_demais.groupby(['ANO', 'UO_COD', 'RECEITA_COD', 'FONTE_COD'])['VL_REC'].sum().reset_index()

# BASE ANALISE
base_analise = pd.concat([base_convenios, base_demais], ignore_index=True)
base_analise['RECEITA_COD'] = base_analise['RECEITA_COD'].fillna('-')
base_analise = base_analise[['ANO', 'UO_COD', 'RECEITA_COD', 'FONTE_COD', 'VL_REC']]

# Pivot the table
base_analise = base_analise.pivot_table(
    index=['UO_COD', 'RECEITA_COD', 'FONTE_COD'],
    columns='ANO',
    values='VL_REC',
    aggfunc='first'
).reset_index()

# Fill NaN values with 0 and round to 2 decimal places
numeric_columns = base_analise.select_dtypes(include=[np.number]).columns
base_analise[numeric_columns] = base_analise[numeric_columns].fillna(0).round(2)

# ALERTAS
base_analise['ANO'] = ANO_REF
base_analise['INTRA_SAUDE'] = is_intra_saude_rec(base_analise)
base_analise['CONVENIOS'] = is_convenios_rec(base_analise)

# Create ALERTAS column with conditions
conditions = [
    (base_analise['INTRA_SAUDE'] == True),
    (base_analise['FONTE_COD'].isin(fontes_convenios)),
    ((base_analise['CONVENIOS'] == True) & ~base_analise['FONTE_COD'].isin(fontes_convenios)),
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

# Final processing
base_analise = adiciona_desc(base_analise, ["RECEITA_COD", "UO_COD"], overwrite=True)
base_analise = base_analise.drop(['ANO', 'INTRA_SAUDE', 'CONVENIOS'], axis=1)
base_analise = base_analise[
    ~((base_analise['UO_COD'] == 4461) | (base_analise['FONTE_COD'] == 58))
] 