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


@st.cache_data
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


@st.cache_data
def load_orcamento_receita(file_path, df_aux):
    try:
        # Lê base garantindo o ponto e virgula
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, sep=';', encoding='latin1')
    except FileNotFoundError:
        st.error(f"⚠️ Arquivo '{file_path}' não encontrado.")
        return pd.DataFrame()

    # Se a leitura falhou e trouxe 1 coluna só, tenta com vírgula (redundância de segurança)
    if len(df.columns) == 1:
        try:
            df = pd.read_csv(file_path, sep=',', encoding='utf-8')
        except:
            pass

    if not df_aux.empty and 'Fonte' in df.columns:
        # Extrai os dígitos iniciais da fonte para garantir o cruzamento
        df['fonte_cod_temp'] = df['Fonte'].astype(
            str).str.extract(r'^(\d+)')[0]
        df['fonte_cod_temp'] = df['fonte_cod_temp'].fillna(
            df['Fonte'].astype(str).str.strip())

        df = df.merge(df_aux, left_on='fonte_cod_temp',
                      right_on='CD_FONTE', how='left')
        df['passivel_analise_dcmefo'] = df['Analise DCMEFO'].apply(
            lambda x: 'Sim' if str(x).strip().upper() == 'SIM' else 'Não'
        )
        df.drop(columns=['fonte_cod_temp'], inplace=True, errors='ignore')
    else:
        df['passivel_analise_dcmefo'] = 'Não'

    # Concatenações da base LDO 2027
    if 'Código da Unidade' in df.columns and 'Unidade Orçamentária' in df.columns:
        df['Unidade Orçamentária_concat'] = df['Código da Unidade'].astype(
            str) + ' - ' + df['Unidade Orçamentária'].astype(str)

    if 'Classificação da Receita' in df.columns and 'Descrição da Receita' in df.columns:
        df['Classificação da Receita_concat'] = df['Classificação da Receita'].astype(
            str) + ' - ' + df['Descrição da Receita'].astype(str)

    # Tratamento numérico para o Valor LDO
    if 'Valor LDO' in df.columns:
        if df['Valor LDO'].dtype == object:
            df['Valor LDO'] = df['Valor LDO'].astype(str).str.replace(
                '.', '', regex=False).str.replace(',', '.', regex=False)
        df['Valor LDO'] = pd.to_numeric(
            df['Valor LDO'], errors='coerce').fillna(0)

    return df


@st.cache_data
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

    # Colunas Concatenadas
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

df_auxiliar = load_aux_data(ARQUIVO_AUXILIAR)
df_receita = load_data(ARQUIVO_RECEITA, df_auxiliar)
df_fonte = load_data(ARQUIVO_FONTE, df_auxiliar)
df_orcamento = load_orcamento_receita(ARQUIVO_ORCAMENTO, df_auxiliar)
df_dcmefo_base = load_analise_dcmefo(ARQUIVO_ANALISE_DCMEFO)

# -----------------------------------------------------------------------------
# Componentes Reutilizáveis
# -----------------------------------------------------------------------------


def exibir_resumo_alertas(df):
    st.markdown("### Resumo de Alertas")
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
    """Aplica o estilo de formatação brasileira (R$) nas colunas financeiras."""
    colunas_anos = ['2023', '2024', '2025_reest', '2026', 'Valor LDO']
    colunas_formatar = [col for col in colunas_anos if col in colunas_finais]

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
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_filtrado[colunas_finais]), file_name='visao_geral.csv', mime='text/csv')

    st.dataframe(formatar_tabela_ptbr(df_filtrado, colunas_finais),
                 use_container_width=True, hide_index=True)


def tela_fonte_recursos():
    st.title("Análise por Fonte de Recursos")
    df_filtrado = aplicar_filtros_comuns(df_fonte, is_visao_geral=False)
    exibir_resumo_alertas(df_filtrado)

    colunas_exibicao = ['UO', 'Fonte de Recursos', '2023',
                        '2024', '2025_reest', '2026', 'Alerta_Visual']
    colunas_finais = [
        col for col in colunas_exibicao if col in df_filtrado.columns]

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("### 📋 Detalhamento (Fonte de Recursos)")
    with col2:
        st.download_button(label="📥 Exportar para CSV", data=convert_df_to_csv(
            df_filtrado[colunas_finais]), file_name='fontes.csv', mime='text/csv')

    st.dataframe(formatar_tabela_ptbr(df_filtrado, colunas_finais),
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
        "Passível de análise DCMEFO?", opcoes_dcmefo, default=opcoes_dcmefo)

    opcoes_uo_concat = sorted(df_orcamento['Unidade Orçamentária_concat'].dropna(
    ).unique().tolist()) if 'Unidade Orçamentária_concat' in df_orcamento.columns else []
    filtro_uo_concat = st.sidebar.multiselect(
        "Unidade Orçamentária", opcoes_uo_concat)

    opcoes_fonte = sorted(df_orcamento['Fonte'].dropna().unique(
    ).tolist()) if 'Fonte' in df_orcamento.columns else []
    filtro_fonte = st.sidebar.multiselect("Fonte de Recursos", opcoes_fonte)

    opcoes_class_concat = sorted(df_orcamento['Classificação da Receita_concat'].dropna(
    ).unique().tolist()) if 'Classificação da Receita_concat' in df_orcamento.columns else []
    filtro_classificacao = st.sidebar.multiselect(
        "Classificação da Receita", opcoes_class_concat)

    opcoes_metodologia = sorted(df_orcamento['Metodologia de cálculo e premissas utilizadas'].dropna(
    ).unique().tolist()) if 'Metodologia de cálculo e premissas utilizadas' in df_orcamento.columns else []
    filtro_metodologia = st.sidebar.multiselect(
        "Metodologias e Premissas", opcoes_metodologia)

    df_filtrado = df_orcamento.copy()

    if filtro_dcmefo:
        df_filtrado = df_filtrado[df_filtrado['passivel_analise_dcmefo'].isin(
            filtro_dcmefo)]
    if filtro_uo_concat:
        df_filtrado = df_filtrado[df_filtrado['Unidade Orçamentária_concat'].isin(
            filtro_uo_concat)]
    if filtro_fonte:
        df_filtrado = df_filtrado[df_filtrado['Fonte'].isin(filtro_fonte)]
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
    if 'Fonte' in df_filtrado.columns:
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
        "Unidade Orçamentária", opcoes_uo_concat)

    opcoes_fonte_concat = sorted(df_dcmefo_base['Fonte de recursos_concat'].dropna(
    ).unique().tolist()) if 'Fonte de recursos_concat' in df_dcmefo_base.columns else []
    filtro_fonte_concat = st.sidebar.multiselect(
        "Fonte de Recursos", opcoes_fonte_concat)

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


# -----------------------------------------------------------------------------
# Menu de Navegação
# -----------------------------------------------------------------------------
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Selecione a Página:", [
                        "Visão Geral", "Fonte de Recursos", "LDO 2027", "Análise DCMEFO"])

if menu == "Visão Geral":
    tela_visao_geral()
elif menu == "Fonte de Recursos":
    tela_fonte_recursos()
elif menu == "LDO 2027":
    tela_ldo_2027()
elif menu == "Análise DCMEFO":
    tela_analise_dcmefo()
