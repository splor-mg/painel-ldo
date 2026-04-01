import streamlit as st
import pandas as pd
import unicodedata
import subprocess
from datetime import datetime, timezone, timedelta

# -----------------------------------------------------------------------------
# Configuração da Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitoramento de Receitas - LDO",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# Dicionário de Emojis/Cores para Alertas
# -----------------------------------------------------------------------------
ALERT_MAP = {
    "OK": "🟢",
    "RECEITA A SER INFORMADA PELA DCGCE/SEPLAG": "🟣",  # Lilás
    "ATENCAO": "🟠",
    "VALOR DISCREPANTE": "⚠️",
    "RECEITA NAO ESTIMADA": "🔴",
    "RECEITA DE REPASSE DO FES E LANCADA PELA SPLOR": "🔵",  # Azul
    "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA": "🟤"  # Marrom
}


def normalizar_texto(texto):
    """Remove acentos, espaços extras e deixa tudo maiúsculo para evitar falhas no cruzamento."""
    if pd.isna(texto):
        return ""
    texto = str(texto).upper().strip()
    texto_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', texto)
                               if unicodedata.category(c) != 'Mn')
    return texto_sem_acento


def get_alert_icon(alert_text):
    texto_norm = normalizar_texto(alert_text)
    return ALERT_MAP.get(texto_norm, "📌")


@st.cache_data(ttl="1h")
def get_data_atualizacao():
    """Consulta o histórico interno do próprio Git para saber o horário do último push."""
    try:
        # Roda um comando invisível do git para pegar a data do último commit (em formato ISO)
        resultado = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cI']).decode('utf-8').strip()

        # Converte o texto para formato de Data e Hora
        dt_commit = datetime.fromisoformat(resultado)

        # Converte para o padrão Universal (UTC) e depois desconta 3 horas para Brasília
        dt_utc = dt_commit.astimezone(timezone.utc)
        dt_brasilia = dt_utc - timedelta(hours=3)

        return dt_brasilia.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return "Indisponível"

# -----------------------------------------------------------------------------
# Função para Exportar CSV
# -----------------------------------------------------------------------------


@st.cache_data
def convert_df_to_csv(df):
    """Converte o dataframe para CSV formatado para abrir corretamente no Excel (PT-BR)."""
    return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

# -----------------------------------------------------------------------------
# Carregamento e Tratamento de Dados
# -----------------------------------------------------------------------------


@st.cache_data(ttl="1h")
def load_uo_data(file_path):
    """Carrega a base auxiliar de Unidades Orçamentárias para obter as siglas (Apenas Ano 2026)."""
    try:
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo '{file_path}' não encontrado.")
        return pd.DataFrame()

    if len(df.columns) == 1:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
        except:
            pass

    # Filtra os dados apenas para o ano de 2026
    col_ano = next((col for col in df.columns if str(
        col).strip().lower() == 'ano'), None)
    if col_ano:
        df = df[df[col_ano].astype(str).str.strip() == '2026']

    if 'uo_cod' in df.columns:
        df['uo_cod'] = df['uo_cod'].astype(str)
    return df


@st.cache_data(ttl="1h")
def load_fonte_recurso_data(file_path):
    """Carrega a base auxiliar de Fontes de Recurso para obter as descrições (Apenas Ano 2026)."""
    try:
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo '{file_path}' não encontrado.")
        return pd.DataFrame()

    if len(df.columns) == 1:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
        except:
            pass

    # Filtra os dados apenas para o ano de 2026
    col_ano = next((col for col in df.columns if str(
        col).strip().lower() == 'ano'), None)
    if col_ano:
        df = df[df[col_ano].astype(str).str.strip() == '2026']

    if 'fonte_cod' in df.columns:
        df['fonte_cod'] = df['fonte_cod'].astype(str).str.strip()
    return df


@st.cache_data(ttl="1h")
def load_aux_data(file_path):
    try:
        df_aux = pd.read_csv(file_path, sep=';', encoding='latin1')
        df_aux['CD_FONTE'] = df_aux['CD_FONTE'].astype(str)
        return df_aux[['CD_FONTE', 'Analise DCMEFO']]
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo auxiliar '{file_path}' não encontrado.")
        return pd.DataFrame()
    except Exception:
        try:
            df_aux = pd.read_csv(file_path)
            df_aux['CD_FONTE'] = df_aux['CD_FONTE'].astype(str)
            return df_aux[['CD_FONTE', 'Analise DCMEFO']]
        except Exception as e:
            st.error(f"⚠️ Erro ao ler a base auxiliar: {e}")
            return pd.DataFrame()


@st.cache_data(ttl="1h")
def load_data(file_path, df_aux):
    try:
        # Tenta ler com virgula (padrão)
        df = pd.read_csv(file_path)
        if len(df.columns) == 1:  # Se leu tudo como 1 coluna, forçar ponto e vírgula
            df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo principal '{file_path}' não encontrado.")
        return pd.DataFrame()
    except Exception:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')

    if 'fonte_cod' in df.columns:
        df['fonte_cod'] = df['fonte_cod'].astype(str)
        df_aux_unique = df_aux.drop_duplicates(subset=['CD_FONTE'])
        df = df.merge(df_aux_unique, left_on='fonte_cod',
                      right_on='CD_FONTE', how='left')

        df['passivel_analise_dcmefo'] = df['Analise DCMEFO'].apply(
            lambda x: 'Sim' if str(x).strip().upper() == 'SIM' else 'Não'
        )
    else:
        df['passivel_analise_dcmefo'] = 'Não'

    if 'uo_cod' in df.columns and 'uo_sigla' in df.columns:
        df['UO'] = df['uo_cod'].astype(str) + ' - ' + df['uo_sigla']

    if 'fonte_cod' in df.columns and 'fonte_desc' in df.columns:
        df['Fonte de Recursos'] = df['fonte_cod'].astype(
            str) + ' - ' + df['fonte_desc']

    if 'receita_cod' in df.columns and 'receita_desc' in df.columns:
        df['Classificação da Receita'] = df['receita_cod'].astype(
            str) + ' - ' + df['receita_desc']

    if 'alertas' in df.columns:
        df['Alerta_Visual'] = df['alertas'].apply(
            lambda x: f"{get_alert_icon(x)} {x}")

    return df


@st.cache_data(ttl="1h")
def load_orcamento_receita(file_path, df_aux, df_uo, df_fonte_recurso):
    try:
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo '{file_path}' não encontrado.")
        return pd.DataFrame()

    if len(df.columns) == 1:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
        except:
            pass

    if not df_aux.empty and 'Fonte' in df.columns:
        df['fonte_cod_temp'] = df['Fonte'].astype(
            str).str.extract(r'^(\d+)')[0]
        df['fonte_cod_temp'] = df['fonte_cod_temp'].fillna(
            df['Fonte'].astype(str).str.strip())

        df_aux_unique = df_aux.drop_duplicates(subset=['CD_FONTE'])

        df = df.merge(df_aux_unique, left_on='fonte_cod_temp',
                      right_on='CD_FONTE', how='left')
        df['passivel_analise_dcmefo'] = df['Analise DCMEFO'].apply(
            lambda x: 'Sim' if str(x).strip().upper() == 'SIM' else 'Não'
        )
        df.drop(columns=['fonte_cod_temp'], inplace=True, errors='ignore')
    else:
        df['passivel_analise_dcmefo'] = 'Não'

    # Concatenações da base LDO 2027 (Cruzamento com uo.csv já filtrada em 2026)
    if not df_uo.empty and 'Código da Unidade' in df.columns and 'uo_cod' in df_uo.columns:
        df['Código da Unidade'] = df['Código da Unidade'].astype(str)
        df_uo_unique = df_uo[['uo_cod', 'uo_sigla']].drop_duplicates(subset=[
                                                                     'uo_cod'])

        df = df.merge(df_uo_unique, left_on='Código da Unidade',
                      right_on='uo_cod', how='left')

        if 'Unidade Orçamentária' in df.columns:
            df['uo_sigla'] = df['uo_sigla'].fillna(
                df['Unidade Orçamentária'].astype(str))
        else:
            df['uo_sigla'] = df['uo_sigla'].fillna('')

        df['Unidade Orçamentária_concat'] = df['Código da Unidade'] + \
            ' - ' + df['uo_sigla'].astype(str)
        df.drop(columns=['uo_cod'], inplace=True, errors='ignore')
    elif 'Código da Unidade' in df.columns and 'Unidade Orçamentária' in df.columns:
        df['Unidade Orçamentária_concat'] = df['Código da Unidade'].astype(
            str) + ' - ' + df['Unidade Orçamentária'].astype(str)

    # Concatenações da base LDO 2027 (Cruzamento com fonte_recurso.csv já filtrada em 2026)
    if not df_fonte_recurso.empty and 'Fonte' in df.columns and 'fonte_cod' in df_fonte_recurso.columns:
        df['Fonte_str'] = df['Fonte'].astype(str).str.strip()
        df_fonte_recurso['fonte_cod_str'] = df_fonte_recurso['fonte_cod'].astype(
            str).str.strip()

        df_fr_unique = df_fonte_recurso[['fonte_cod_str', 'fonte_desc']].drop_duplicates(
            subset=['fonte_cod_str'])

        df = df.merge(df_fr_unique, left_on='Fonte_str',
                      right_on='fonte_cod_str', how='left')
        df['fonte_desc'] = df['fonte_desc'].fillna('')

        df['Fonte_concat'] = df.apply(
            lambda row: f"{row['Fonte']} - {row['fonte_desc']}" if str(
                row['fonte_desc']).strip() != '' else str(row['Fonte']),
            axis=1
        )
        df.drop(columns=['fonte_cod_str', 'Fonte_str'],
                inplace=True, errors='ignore')
    elif 'Fonte' in df.columns:
        df['Fonte_concat'] = df['Fonte'].astype(str)

    if 'Classificação da Receita' in df.columns and 'Descrição da Receita' in df.columns:
        df['Classificação da Receita_concat'] = df['Classificação da Receita'].astype(
            str) + ' - ' + df['Descrição da Receita'].astype(str)

    if 'Valor LDO' in df.columns:
        if df['Valor LDO'].dtype == object:
            df['Valor LDO'] = df['Valor LDO'].astype(str).str.replace(
                '.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor LDO'] = pd.to_numeric(
            df['Valor LDO'], errors='coerce').fillna(0)

    return df


@st.cache_data(ttl="1h")
def load_analise_dcmefo(file_path):
    try:
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo '{file_path}' não encontrado.")
        return pd.DataFrame()

    if len(df.columns) == 1:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
        except:
            pass

    if 'uo_cod' in df.columns and 'uo_sigla' in df.columns:
        df['Unidade Orçamentária_concat'] = df['uo_cod'].astype(
            str) + ' - ' + df['uo_sigla'].astype(str)

    if 'fonte_cod' in df.columns and 'fonte_desc' in df.columns:
        df['Fonte de recursos_concat'] = df['fonte_cod'].astype(
            str) + ' - ' + df['fonte_desc'].astype(str)

    return df


# Caminhos dos arquivos
ARQUIVO_AUXILIAR = 'datapackages/tabelas_auxiliares/tab_auxiliar_fte_dcmefo.csv'
ARQUIVO_RECEITA = 'data/receita_analise.csv'
ARQUIVO_FONTE = 'data/fonte_analise.csv'
ARQUIVO_ORCAMENTO = 'datapackages/ppo_2027/data/Orcamento_Receita.csv'
ARQUIVO_ANALISE_DCMEFO = 'datapackages/tabelas_auxiliares/analise_dcmefo.csv'
ARQUIVO_UO = 'datapackages/dados-aux-classificadores/data/uo.csv'
ARQUIVO_FONTE_RECURSO = 'datapackages/dados-aux-classificadores/data/fonte_recurso.csv'

# Carregamento executado em ordem de dependência
df_auxiliar = load_aux_data(ARQUIVO_AUXILIAR)
df_uo = load_uo_data(ARQUIVO_UO)
df_fonte_recurso = load_fonte_recurso_data(ARQUIVO_FONTE_RECURSO)
df_receita = load_data(ARQUIVO_RECEITA, df_auxiliar)
df_fonte = load_data(ARQUIVO_FONTE, df_auxiliar)
df_orcamento = load_orcamento_receita(
    ARQUIVO_ORCAMENTO, df_auxiliar, df_uo, df_fonte_recurso)
df_dcmefo_base = load_analise_dcmefo(ARQUIVO_ANALISE_DCMEFO)

# -----------------------------------------------------------------------------
# Componentes Reutilizáveis
# -----------------------------------------------------------------------------


def exibir_resumo_alertas(df):
    st.markdown("### 📊 Resumo de Alertas")
    alert_counts = df['alertas'].value_counts().reset_index()
    alert_counts.columns = ['Alerta', 'Quantidade']

    if not alert_counts.empty:
        cols = st.columns(len(alert_counts))
        for i, row in alert_counts.iterrows():
            alerta_texto = row['Alerta']
            icone = get_alert_icon(alerta_texto)
            qtd = row['Quantidade']
            cols[i].metric(label=f"{icone} {alerta_texto}", value=qtd)
    else:
        st.info("Nenhum alerta encontrado para os filtros selecionados.")
    st.markdown("---")


def aplicar_filtros_comuns(df, is_visao_geral=True):
    st.sidebar.header("Filtros")
    prefix = "vg" if is_visao_geral else "fr"

    opcoes_dcmefo = sorted(df['passivel_analise_dcmefo'].unique().tolist())
    filtro_dcmefo = st.sidebar.multiselect(
        "Passível de análise DCMEFO?", opcoes_dcmefo, key=f"filtro_{prefix}_dcmefo")

    opcoes_uo = sorted(df['UO'].dropna().unique().tolist())
    filtro_uo = st.sidebar.multiselect(
        "Unidade Orçamentária (UO)", opcoes_uo, key=f"filtro_{prefix}_uo")

    opcoes_fonte = sorted(df['Fonte de Recursos'].dropna().unique().tolist())
    filtro_fonte = st.sidebar.multiselect(
        "Fonte de Recursos", opcoes_fonte, key=f"filtro_{prefix}_fonte")

    filtro_receita = []
    if is_visao_geral and 'Classificação da Receita' in df.columns:
        opcoes_receita = sorted(
            df['Classificação da Receita'].dropna().unique().tolist())
        filtro_receita = st.sidebar.multiselect(
            "Classificação da Receita", opcoes_receita, key=f"filtro_{prefix}_receita")

    opcoes_alerta = sorted(df['alertas'].dropna().unique().tolist())
    filtro_alerta = st.sidebar.multiselect(
        "Tipo de Alerta", opcoes_alerta, key=f"filtro_{prefix}_alerta")

    df_filtrado = df.copy()

    if filtro_dcmefo:
        df_filtrado = df_filtrado[df_filtrado['passivel_analise_dcmefo'].isin(
            filtro_dcmefo)]
    if filtro_uo:
        df_filtrado = df_filtrado[df_filtrado['UO'].isin(filtro_uo)]
    if filtro_fonte:
        df_filtrado = df_filtrado[df_filtrado['Fonte de Recursos'].isin(
            filtro_fonte)]
    if is_visao_geral and filtro_receita:
        df_filtrado = df_filtrado[df_filtrado['Classificação da Receita'].isin(
            filtro_receita)]
    if filtro_alerta:
        df_filtrado = df_filtrado[df_filtrado['alertas'].isin(filtro_alerta)]

    return df_filtrado


def formatar_tabela_ptbr(df_filtrado, colunas_finais):
    colunas_anos = ['2023', '2024', '2025',
                    '2026 Reest', '2027 LDO', 'Valor LDO']
    colunas_formatar = [col for col in colunas_anos if col in colunas_finais]

    return df_filtrado[colunas_finais].style.format(
        subset=colunas_formatar,
        precision=2,
        thousands='.',
        decimal=','
    )

# -----------------------------------------------------------------------------
# Lógica de Limpeza de Filtros (Callback)
# -----------------------------------------------------------------------------


def limpar_filtros():
    for key in list(st.session_state.keys()):
        if key.startswith("filtro_"):
            st.session_state[key] = []


# -----------------------------------------------------------------------------
# Menu de Navegação e Botões Globais
# -----------------------------------------------------------------------------
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione a Página:", [
                        "Visão Geral", "Fonte de Recursos", "LDO 2027", "Análise DCMEFO"])

st.sidebar.markdown("---")
st.sidebar.button("🧹 Limpar Todos os Filtros",
                  on_click=limpar_filtros, use_container_width=True)
st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# Cabeçalho Global (Aparece no topo direito de todas as telas)
# -----------------------------------------------------------------------------
data_att = get_data_atualizacao()
col_vazia, col_info = st.columns([0.65, 0.35])
with col_info:
    st.markdown(
        f"<div style='text-align: right; color: gray;'><small>🔄 Última atualização dos dados: <b>{data_att}</b></small></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Telas da Aplicação
# -----------------------------------------------------------------------------


def tela_visao_geral():
    st.title("Visão Geral - Previsão de Receitas")
    df_filtrado = aplicar_filtros_comuns(df_receita, is_visao_geral=True)
    exibir_resumo_alertas(df_filtrado)

    mapa_colunas = {
        'uo_cod': 'UO cod',
        'uo_sigla': 'UO',
        'receita_cod': 'Classificação Receita cod',
        'receita_desc': 'Classificação da Receita',
        'fonte_cod': 'Fonte cod',
        'fonte_desc': 'Fonte de Recursos',
        '2024': '2024',
        '2025': '2025',
        'reestimativa_2026': '2026 Reest',
        '2027': '2027 LDO',
        'Alerta_Visual': 'alertas'
    }

    colunas_presentes = [
        col for col in mapa_colunas.keys() if col in df_filtrado.columns]
    df_display = df_filtrado[colunas_presentes].rename(columns=mapa_colunas)
    colunas_finais = df_display.columns.tolist()

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Visão Geral)")
    with col2:
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_display), file_name='visao_geral.csv', mime='text/csv')

    st.dataframe(formatar_tabela_ptbr(df_display, colunas_finais),
                 use_container_width=True, hide_index=True)


def tela_fonte_recursos():
    st.title("Análise por Fonte de Recursos")
    df_filtrado = aplicar_filtros_comuns(df_fonte, is_visao_geral=False)
    exibir_resumo_alertas(df_filtrado)

    mapa_colunas = {
        'uo_cod': 'UO cod',
        'uo_sigla': 'UO',
        'fonte_cod': 'Fonte cod',
        'fonte_desc': 'Fonte de Recursos',
        '2024': '2024',
        '2025': '2025',
        'reestimativa_2026': '2026 Reest',
        '2027': '2027 LDO',
        'Alerta_Visual': 'alertas'
    }

    colunas_presentes = [
        col for col in mapa_colunas.keys() if col in df_filtrado.columns]
    df_display = df_filtrado[colunas_presentes].rename(columns=mapa_colunas)
    colunas_finais = df_display.columns.tolist()

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Fonte de Recursos)")
    with col2:
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_display), file_name='fontes.csv', mime='text/csv')

    st.dataframe(formatar_tabela_ptbr(df_display, colunas_finais),
                 use_container_width=True, hide_index=True)


def tela_ldo_2027():
    st.title("LDO 2027")
    if df_orcamento.empty:
        st.warning("Base de dados Orcamento_Receita não encontrada ou vazia.")
        return

    st.sidebar.header("Filtros LDO 2027")

    opcoes_dcmefo = sorted(
        df_orcamento['passivel_analise_dcmefo'].unique().tolist())
    filtro_dcmefo = st.sidebar.multiselect(
        "Passível de análise DCMEFO?", opcoes_dcmefo, key="filtro_ldo_dcmefo")

    opcoes_uo_concat = sorted(df_orcamento['Unidade Orçamentária_concat'].dropna(
    ).unique().tolist()) if 'Unidade Orçamentária_concat' in df_orcamento.columns else []
    filtro_uo_concat = st.sidebar.multiselect(
        "Unidade Orçamentária", opcoes_uo_concat, key="filtro_ldo_uo")

    opcoes_fonte = sorted(df_orcamento['Fonte_concat'].dropna().unique(
    ).tolist()) if 'Fonte_concat' in df_orcamento.columns else []
    filtro_fonte = st.sidebar.multiselect(
        "Fonte de Recursos", opcoes_fonte, key="filtro_ldo_fonte")

    opcoes_class_concat = sorted(df_orcamento['Classificação da Receita_concat'].dropna(
    ).unique().tolist()) if 'Classificação da Receita_concat' in df_orcamento.columns else []
    filtro_classificacao = st.sidebar.multiselect(
        "Classificação da Receita", opcoes_class_concat, key="filtro_ldo_classificacao")

    opcoes_metodologia = sorted(df_orcamento['Metodologia de cálculo e premissas utilizadas'].dropna(
    ).unique().tolist()) if 'Metodologia de cálculo e premissas utilizadas' in df_orcamento.columns else []
    filtro_metodologia = st.sidebar.multiselect(
        "Metodologias e Premissas", opcoes_metodologia, key="filtro_ldo_metodologia")

    df_filtrado = df_orcamento.copy()

    if filtro_dcmefo:
        df_filtrado = df_filtrado[df_filtrado['passivel_analise_dcmefo'].isin(
            filtro_dcmefo)]
    if filtro_uo_concat:
        df_filtrado = df_filtrado[df_filtrado['Unidade Orçamentária_concat'].isin(
            filtro_uo_concat)]
    if filtro_fonte:
        df_filtrado = df_filtrado[df_filtrado['Fonte_concat'].isin(
            filtro_fonte)]
    if filtro_classificacao:
        df_filtrado = df_filtrado[df_filtrado['Classificação da Receita_concat'].isin(
            filtro_classificacao)]
    if filtro_metodologia:
        df_filtrado = df_filtrado[df_filtrado['Metodologia de cálculo e premissas utilizadas'].isin(
            filtro_metodologia)]

    if 'Valor LDO' in df_filtrado.columns:
        total_valor = df_filtrado['Valor LDO'].sum()
        total_formatado = f"R$ {total_valor:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", ".")
        st.metric(label="Total Valor LDO", value=total_formatado)
        st.markdown("---")

    df_display = pd.DataFrame()
    if 'Unidade Orçamentária_concat' in df_filtrado.columns:
        df_display['Unidade Orçamentária'] = df_filtrado['Unidade Orçamentária_concat']
    if 'Fonte_concat' in df_filtrado.columns:
        df_display['Fonte de Recursos'] = df_filtrado['Fonte_concat']
    elif 'Fonte' in df_filtrado.columns:
        df_display['Fonte de Recursos'] = df_filtrado['Fonte']
    if 'Classificação da Receita_concat' in df_filtrado.columns:
        df_display['Classificação da Receita'] = df_filtrado['Classificação da Receita_concat']
    if 'Metodologia de cálculo e premissas utilizadas' in df_filtrado.columns:
        df_display['Metodologia e Premissas'] = df_filtrado['Metodologia de cálculo e premissas utilizadas']
    if 'Valor LDO' in df_filtrado.columns:
        df_display['Valor LDO'] = df_filtrado['Valor LDO']

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (LDO 2027)")
    with col2:
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_display), file_name='ldo_2027.csv', mime='text/csv')

    st.dataframe(formatar_tabela_ptbr(df_display, df_display.columns.tolist(
    )), use_container_width=True, hide_index=True)


def tela_analise_dcmefo():
    st.title("Análise DCMEFO")
    if df_dcmefo_base.empty:
        st.warning("Base de dados analise_dcmefo não encontrada ou vazia.")
        return

    st.sidebar.header("Filtros Análise DCMEFO")

    opcoes_uo_concat = sorted(df_dcmefo_base['Unidade Orçamentária_concat'].dropna(
    ).unique().tolist()) if 'Unidade Orçamentária_concat' in df_dcmefo_base.columns else []
    filtro_uo_concat = st.sidebar.multiselect(
        "Unidade Orçamentária", opcoes_uo_concat, key="filtro_analise_uo")

    opcoes_fonte_concat = sorted(df_dcmefo_base['Fonte de recursos_concat'].dropna(
    ).unique().tolist()) if 'Fonte de recursos_concat' in df_dcmefo_base.columns else []
    filtro_fonte_concat = st.sidebar.multiselect(
        "Fonte de Recursos", opcoes_fonte_concat, key="filtro_analise_fonte")

    df_filtrado = df_dcmefo_base.copy()

    if filtro_uo_concat:
        df_filtrado = df_filtrado[df_filtrado['Unidade Orçamentária_concat'].isin(
            filtro_uo_concat)]
    if filtro_fonte_concat:
        df_filtrado = df_filtrado[df_filtrado['Fonte de recursos_concat'].isin(
            filtro_fonte_concat)]

    df_display = pd.DataFrame()
    if 'Unidade Orçamentária_concat' in df_filtrado.columns:
        df_display['Unidade Orçamentária'] = df_filtrado['Unidade Orçamentária_concat']
    if 'Fonte de recursos_concat' in df_filtrado.columns:
        df_display['Fonte de recursos'] = df_filtrado['Fonte de recursos_concat']
    if 'analise_dcmefo' in df_filtrado.columns:
        df_display['Análise DCMEFO'] = df_filtrado['analise_dcmefo']

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Análise DCMEFO)")
    with col2:
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_display), file_name='analise_dcmefo.csv', mime='text/csv')

    st.dataframe(df_display, use_container_width=True, hide_index=True)


# Execução do roteador de telas
if menu == "Visão Geral":
    tela_visao_geral()
elif menu == "Fonte de Recursos":
    tela_fonte_recursos()
elif menu == "LDO 2027":
    tela_ldo_2027()
elif menu == "Análise DCMEFO":
    tela_analise_dcmefo()
