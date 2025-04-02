from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from rpy2.robjects import StrVector
import unidecode


def clean_column_names(column_name):
    """
    Reproduce the LOA project data cleansing on the dataframe to be able to use relatorios functions
    """

    # Replace white spaces with dots
    column_name = column_name.replace(" ", ".")

    # Convert to unaccented equivalents
    column_name = unidecode.unidecode(column_name)

    # Convert to lower case
    column_name = column_name.lower()

    return column_name


# Activate the automatic conversion between R data frames and pandas DataFrames
pandas2ri.activate()
base = importr('base')


# You can convert a R package to a python object and use it in the python env
relatorios = importr('relatorios')


def is_convenios_rec(base_analise):

    base_analise_relatorios =  base_analise.rename(columns={'ano': 'ANO', 'receita_cod': 'RECEITA_COD'})
    base_analise_rpy = pandas2ri.py2rpy(base_analise_relatorios)
    
    result = relatorios.is_convenios_rec(base_analise_rpy)
    result_pd = pandas2ri.rpy2py(result).astype(bool)
    
    return result_pd


def is_intra_saude_rec(base_analise):

    base_analise_relatorios =  base_analise.rename(columns={'ano': 'ANO', 'receita_cod': 'RECEITA_COD'})
    base_analise_rpy = pandas2ri.py2rpy(base_analise_relatorios)
    

    result = relatorios.is_intra_saude_rec(base_analise_rpy)
    result_pd = pandas2ri.rpy2py(result).astype(bool)
    return result_pd


def adiciona_desc(base_analise, target_columns=['RECEITA_COD', 'UO_COD', 'FONTE_COD'], overwrite=True):


    base_analise_relatorios =  base_analise.rename(
        columns={'ano': 'ANO', 
                'receita_cod': 'RECEITA_COD',
                'uo_cod': 'UO_COD',
                'fonte_cod': 'FONTE_COD'}
        )
    
    base_analise_rpy = pandas2ri.py2rpy(base_analise_relatorios)
    target_columns_rpy = StrVector(target_columns)

    # R
    result = relatorios.adiciona_desc(base=base_analise_rpy, 
                                      columns = target_columns_rpy, 
                                      overwrite=overwrite)
    
    result_pd = pandas2ri.rpy2py(result)

    return result_pd

