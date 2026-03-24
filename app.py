import streamlit as st
import pandas as pd
import unicodedata

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
# Chaves sem acentos para garantir o cruzamento correto com qualquer base
ALERT_MAP = {
    "OK": "🟢",
    "RECEITA A SER INFORMADA PELA DCGCE/SEPLAG": "⚪",
    "ATENCAO": "🟠",
    "VALOR DISCREPANTE": "⚠️",
    "RECEITA NAO ESTIMADA": "🔴",
    "RECEITA DE REPASSE DO FES E LANCADA PELA SPLOR": "🔘",
    "RECEITA DE CONVENIOS EM FONTE NAO ESPERADA": "⚪"
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


@st.cache_data
def load_aux_data(file_path):
    """Carrega a tabela auxiliar de classificação da DCMEFO."""
    try:
        df_aux = pd.read_csv(file_path, sep=';', encoding='latin1')
        df_aux['CD_FONTE'] = df_aux['CD_FONTE'].astype(str)
        return df_aux[['CD_FONTE', 'Analise DCMEFO']]
    except FileNotFoundError:
        st.error(
            f"⚠️ Arquivo auxiliar '{file_path}' não encontrado. Verifique o caminho da pasta.")
        st.stop()
    except Exception as e:
        st.error(f"⚠️ Erro ao ler a base auxiliar: {e}")
        st.stop()


@st.cache_data
def load_data(file_path, df_aux):
    """Carrega as bases principais e faz o cruzamento com a tabela auxiliar."""
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(
            f"⚠️ Arquivo principal '{file_path}' não encontrado. Verifique o caminho da pasta.")
        st.stop()

    if 'fonte_cod' in df.columns:
        df['fonte_cod'] = df['fonte_cod'].astype(str)
        df = df.merge(df_aux, left_on='fonte_cod',
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


# Caminhos dos arquivos atualizados
ARQUIVO_AUXILIAR = 'datapackages/tabelas_auxiliares/tab_auxiliar_fte_dcmefo.csv'
ARQUIVO_RECEITA = 'data/receita_analise.csv'
ARQUIVO_FONTE = 'data/fonte_analise.csv'

df_auxiliar = load_aux_data(ARQUIVO_AUXILIAR)
df_receita = load_data(ARQUIVO_RECEITA, df_auxiliar)
df_fonte = load_data(ARQUIVO_FONTE, df_auxiliar)

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

    opcoes_dcmefo = sorted(df['passivel_analise_dcmefo'].unique().tolist())
    filtro_dcmefo = st.sidebar.multiselect(
        "Passível de análise DCMEFO?", opcoes_dcmefo, default=opcoes_dcmefo)

    opcoes_uo = sorted(df['UO'].dropna().unique().tolist())
    filtro_uo = st.sidebar.multiselect("Unidade Orçamentária (UO)", opcoes_uo)

    opcoes_fonte = sorted(df['Fonte de Recursos'].dropna().unique().tolist())
    filtro_fonte = st.sidebar.multiselect("Fonte de Recursos", opcoes_fonte)

    filtro_receita = []
    if is_visao_geral and 'Classificação da Receita' in df.columns:
        opcoes_receita = sorted(
            df['Classificação da Receita'].dropna().unique().tolist())
        filtro_receita = st.sidebar.multiselect(
            "Classificação da Receita", opcoes_receita)

    opcoes_alerta = sorted(df['alertas'].dropna().unique().tolist())
    filtro_alerta = st.sidebar.multiselect("Tipo de Alerta", opcoes_alerta)

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
    """Aplica o estilo de formatação brasileira (R$) nas colunas de anos."""
    colunas_anos = ['2023', '2024', '2025_reest', '2026']
    # Identifica quais colunas de anos realmente existem no dataframe final
    colunas_formatar = [col for col in colunas_anos if col in colunas_finais]

    # Aplica o estilo de milhares com ponto e decimal com vírgula
    return df_filtrado[colunas_finais].style.format(
        subset=colunas_formatar,
        precision=2,
        thousands='.',
        decimal=','
    )

# -----------------------------------------------------------------------------
# Telas da Aplicação
# -----------------------------------------------------------------------------


def tela_visao_geral():
    st.title("Visão Geral - Previsão de Receitas")

    df_filtrado = aplicar_filtros_comuns(df_receita, is_visao_geral=True)
    exibir_resumo_alertas(df_filtrado)

    colunas_exibicao = ['UO', 'Fonte de Recursos', 'Classificação da Receita',
                        '2023', '2024', '2025_reest', '2026', 'Alerta_Visual']
    colunas_finais = [
        col for col in colunas_exibicao if col in df_filtrado.columns]

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Visão Geral)")
    with col2:
        st.download_button(
            label="📥 Exportar para CSV",
            data=convert_df_to_csv(df_filtrado[colunas_finais]),
            file_name='visao_geral_receitas.csv',
            mime='text/csv'
        )

    st.dataframe(formatar_tabela_ptbr(df_filtrado, colunas_finais),
                 use_container_width=True, hide_index=True)


def tela_fonte_recursos():
    st.title("Análise por Fonte de Recursos")

    df_filtrado = aplicar_filtros_comuns(df_fonte, is_visao_geral=False)
    exibir_resumo_alertas(df_filtrado)

    colunas_exibicao = ['UO', 'Fonte de Recursos',
                        '2023', '2024', '2025_reest', '2026', 'Alerta_Visual']
    colunas_finais = [
        col for col in colunas_exibicao if col in df_filtrado.columns]

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Fonte de Recursos)")
    with col2:
        st.download_button(
            label="📥 Exportar para CSV",
            data=convert_df_to_csv(df_filtrado[colunas_finais]),
            file_name='analise_fontes.csv',
            mime='text/csv'
        )

    st.dataframe(formatar_tabela_ptbr(df_filtrado, colunas_finais),
                 use_container_width=True, hide_index=True)


# -----------------------------------------------------------------------------
# Menu de Navegação Lateral
# -----------------------------------------------------------------------------
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione a Página:", [
                        "Visão Geral", "Fonte de Recursos"])

if menu == "Visão Geral":
    tela_visao_geral()
elif menu == "Fonte de Recursos":
    tela_fonte_recursos()
