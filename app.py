import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- PALETA DE CORES (mantida) ---
COLOR_PALETTE = {
    "darkest_green": "#255000",
    "dark_green": "#588100",
    "medium_green": "#8db600",
    "light_green": "#c6da52",
    "very_light_green": "#ffff8b",
    "text_on_dark": "#ffff8b",
    "black": "#000000",
    "gray_text": "#333333"
}

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO (mantido) ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")
st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_PALETTE["very_light_green"]}; color: {COLOR_PALETTE["darkest_green"]}; }}
    .header-bar {{ background-color: {COLOR_PALETTE["darkest_green"]}; padding: 10px 50px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
    .header-bar h1 {{ color: {COLOR_PALETTE["text_on_dark"]}; margin: 0; font-size: 1.8rem; font-weight: 600; }}
    .header-bar .stMarkdown p {{ color: {COLOR_PALETTE["light_green"]}; margin: 0; font-size: 0.9rem; }}
    .header-nav {{ display: flex; gap: 20px; }}
    .header-nav .stMarkdown p {{ color: {COLOR_PALETTE["medium_green"]}; cursor: pointer; transition: color 0.2s; }}
    .header-nav .stMarkdown p:hover {{ color: {COLOR_PALETTE["text_on_dark"]}; }}
    .start-processing-section {{ background-color: {COLOR_PALETTE["medium_green"]}; padding: 40px; text-align: center; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .start-processing-section h2 {{ color: {COLOR_PALETTE["darkest_green"]}; font-size: 2rem; font-weight: 700; margin-bottom: 10px; }}
    .start-processing-section p {{ color: {COLOR_PALETTE["darkest_green"]}; font-size: 1.1rem; }}
    .card {{ background-color: #FFFFFF; border: 1px solid {COLOR_PALETTE["light_green"]}; border-radius: 10px; padding: 25px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    h1, h2, h3 {{ color: {COLOR_PALETTE["darkest_green"]}; }}
    body, p, label, .stMarkdown {{ color: {COLOR_PALETTE["gray_text"]} !important; }}
    .stApp > header, .stApp > div:first-child > div:nth-child(2) > div.stMarkdown, .stApp > div:first-child > div:nth-child(2) > p {{ color: {COLOR_PALETTE["darkest_green"]} !important; }}
    .stButton>button {{ background-color: {COLOR_PALETTE["dark_green"]}; color: {COLOR_PALETTE["text_on_dark"]}; border-radius: 8px; border: none; padding: 10px 24px; font-weight: 500; transition: background-color 0.2s; }}
    .stButton>button:hover {{ background-color: {COLOR_PALETTE["darkest_green"]}; color: {COLOR_PALETTE["text_on_dark"]}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_PALETTE["light_green"]}; border-right: 1px solid {COLOR_PALETTE["dark_green"]}; }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ color: {COLOR_PALETTE["darkest_green"]}; }}
    .st-emotion-cache-115fcme summary, .st-emotion-cache-115fcme button {{ color: {COLOR_PALETTE["darkest_green"]} !important; }}
    .stAlert.stAlert_success {{ background-color: #d4edda; color: #155724; border-color: #c3e6cb; }}
    .stAlert.stAlert_warning {{ background-color: #fff3cd; color: #856404; border-color: #ffeeba; }}
    .stAlert.stAlert_info {{ background-color: #d1ecf1; color: #0c5460; border-color: #bee5eb; }}
    .stAlert.stAlert_error {{ background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }}
    [data-testid="stDataFrame"] .col-header {{ background-color: {COLOR_PALETTE["light_green"]} !important; }}
    [data-testid="stDataFrame"] .col-header-cell {{ color: {COLOR_PALETTE["darkest_green"]} !important; }}
    .upload-area-main .stFileUploader > div:first-child {{ border: 2px dashed {COLOR_PALETTE["dark_green"]}; }}
    .upload-area-main .stFileUploader > div:first-child svg {{ color: {COLOR_PALETTE["dark_green"]}; }}
</style>
""", unsafe_allow_html=True)

@contextmanager
def card_container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO ---
def load_sequentials(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_sequentials(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None: return None, "Nenhum arquivo carregado."
    try:
        if uploaded_file.name.endswith(".xlsx"):
            # Ler todas as colunas como texto para evitar conversão automática
            df = pd.read_excel(uploaded_file, dtype=str)
        else: # TXT
            content = uploaded_file.getvalue().decode('utf-8').splitlines()
            header_line_index = -1
            for i in range(len(content) - 1, -1, -1):
                if content[i].strip():
                    header_line_index = i
                    break
            if header_line_index == -1: return None, "Não foi possível encontrar o cabeçalho no TXT."
            header = [h.strip() for h in content[header_line_index].split('\t')]
            data_lines = content[:header_line_index]
            parsed_data = []
            for line in data_lines:
                if line.strip():
                    cells = [cell.strip() for cell in line.split('\t')]
                    while len(cells) < len(header): cells.append('')
                    parsed_data.append(cells[:len(header)])
            df = pd.DataFrame(parsed_data, columns=header)
            df = df.iloc[::-1].reset_index(drop=True)
        
        # Garante que todas as células sejam strings e preenche vazios
        df = df.astype(str).fillna('')
        
        # --- CORREÇÃO DEFINITIVA APLICADA AQUI ---
        # Garante que a coluna 'Nº DO ITEM' exista antes de limpá-la
        if 'Nº DO ITEM' in df.columns:
            # Remove o '.0' que o Excel adiciona a números inteiros (ex: '1.0' -> '1')
            df['Nº DO ITEM'] = df['Nº DO ITEM'].str.replace(r'\.0$', '', regex=True)
        # --- FIM DA CORREÇÃO ---

        essential_cols = ['Nº DA PEÇA', 'PROCESSO', 'GRUPO DE PRODUTO', 'TÍTULO', 'Nº DO ITEM', 'MATERIAL', 'DIMENSÕES']
        for col in essential_cols:
            if col not in df.columns: df[col] = ''
        
        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)
        
        return df, "Arquivo lido com sucesso."
    except Exception as e: return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df, state_file):
    if df is None or df.empty: return pd.DataFrame(), []
    report_log = []
    sequentials = load_sequentials(state_file)
    report_log.append(f"Estado sequenciais carregado: {sequentials or 'Nenhum'}")
    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{4}$')
    processed_count = 0
    for i, row in df.iterrows():
        if not str(row['PROCESSO']).strip():
            df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
            processed_count += 1
    report_log.append(f"Coluna 'PROCESSO' preenchida para {processed_count} linhas vazias.")
    df['CÓDIGO FINAL'] = ''
    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA'])
        if commercial_pattern.match(num):
            try:
                group, seq = num.split('-')
                seq = int(seq)
                if group not in sequentials or seq > sequentials[group]: sequentials[group] = seq
            except: continue
    report_log.append(f"Sequenciais iniciais ajustados: {sequentials or 'Nenhum'}")
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
            continue
        if row['PROCESSO'] == 'COMERCIAL':
            num = str(row['Nº DA PEÇA'])
            if commercial_pattern.match(num):
                df.loc[i, 'CÓDIGO FINAL'] = num
                continue
            m = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if m:
                g = m.group(1)
                sequentials[g] = sequentials.get(g, 0) + 1
                new_code = f"{g}-{sequentials[g]:04d}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"'{row['TÍTULO']}' recebeu código: {new_code}")
            else: report_log.append(f"'{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")
    df['CÓDIGO FINAL'] = df['CÓDIGO FINAL'].replace('', 'NULO')

    # Ordenação e conversão para maiúsculas primeiro
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    # Lógica de hierarquia executada sobre os dados já limpos e finalizados
    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()
    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts = parts[:-1]
            parent = '.'.join(parts)
            if parent in code_map: return code_map[parent]
        return None
    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(lambda x: find_parent_code(x) or "")
    
    # Adiciona log de sucesso da hierarquia
    parents_found = df['CÓDIGO PAI'].astype(bool).sum()
    report_log.append(f"Hierarquia processada: {parents_found} itens receberam um Código Pai.")

    # Reordenamento de Colunas
    final_order = [col for col in ['Nº DO ITEM', 'TÍTULO', 'Nº DA PEÇA', 'PROCESSO', 'GRUPO DE PRODUTO', 'MATERIAL', 'DIMENSÕES', 'CÓDIGO FINAL', 'CÓDIGO PAI'] if col in df.columns]
    other_cols = [col for col in df.columns if col not in final_order]
    df = df[final_order + other_cols]

    save_sequentials(state_file, sequentials)
    report_log.append(f"Sequenciais salvos em {state_file}")
    num_codes_generated = len([log for log in report_log if 'recebeu código:' in log])
    report_log.insert(0, f"Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    processed_data = out.getvalue()
    return processed_data

# --- INTERFACE ---
st.markdown(f"""<div class="header-bar"><div><h1>SolidWorks BOM Processor</h1><p>Processamento automático de listas de materiais exportadas do SolidWorks</p></div><div class="header-nav"><p>⚡ Processamento Rápido</p><p>📝 Normas Internas</p><p>💾 Export Excel/CSV</p></div></div>""", unsafe_allow_html=True)
with st.sidebar:
    st.header("Configurações")
    st.info("Utilize as opções abaixo para configurar o processamento.", icon="⚙️")
    state_file = st.text_input("Nome do arquivo de estado:", "estado_sequenciais.json", key="state_file_input")
    st.info("Salva os contadores sequenciais para evitar códigos duplicados.", icon="💾")
with st.container():
    st.markdown('<div class="start-processing-section"><h2>Começar Processamento</h2><p>Faça upload do arquivo TXT ou XLSX exportado do SolidWorks.</p></div>', unsafe_allow_html=True)

# Armazena o dataframe bruto no estado da sessão
if 'df_raw' not in st.session_state:
    st.session_state.df_raw = None

with card_container():
    st.subheader("Upload de Arquivo BOM")
    st.write("Faça upload do arquivo TXT ou XLSX exportado do SolidWorks.")
    uploaded_file = st.file_uploader("Clique ou arraste um arquivo", type=['txt','xlsx'], key="main_uploader", help="TXT deve ser separado por tabulação com cabeçalho na última linha.")
    st.markdown('<div class="upload-area-main"></div>', unsafe_allow_html=True)

# Lógica principal da interface
if uploaded_file:
    # Processa os dados brutos e armazena no estado da sessão
    st.session_state.df_raw, msg = load_data(uploaded_file)
    
    # --- NOVA FUNCIONALIDADE: PRÉ-VISUALIZAÇÃO ---
    if st.session_state.df_raw is not None:
        with st.expander("👁️ Pré-visualização dos Dados Carregados (verifique a coluna 'Nº DO ITEM')"):
            st.info("Esta tabela mostra os dados brutos após a limpeza inicial. Verifique se os números de item (ex: '1', '1.1') estão formatados corretamente antes de processar.")
            st.dataframe(st.session_state.df_raw.head(10))
    # --- FIM DA NOVA FUNCIONALIDADE ---
    
    # Botão para iniciar o processamento completo
    if st.button("🚀 Processar Códigos", type="primary"):
        try:
            with st.spinner("Processando..."):
                df_proc, report = process_codes(st.session_state.df_raw.copy(), state_file)
                st.session_state.df_proc = df_proc
                st.session_state.report = report
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado durante o processamento: {e}")
            st.session_state.df_proc = None # Limpa o resultado em caso de erro

# Exibe os resultados se eles existirem no estado da sessão
if 'df_proc' in st.session_state and st.session_state.df_proc is not None:
    tab_relatorio, tab_dados = st.tabs(["📄 Relatório de Processamento", "📊 Lista de Peças Atualizada"])
    with tab_relatorio:
        with card_container():
            st.subheader("Detalhes do Processamento")
            for log in st.session_state.report:
                if "concluído" in log or "Hierarquia processada" in log: st.success(log)
                elif "sem grupo" in log: st.warning(log)
                else: st.info(log)
    with tab_dados:
        with card_container():
            st.subheader("Dados Processados")
            sort_option = st.radio("Classificar por:", ("Padrão","GRUPO DE PRODUTO","PROCESSO"), horizontal=True, key="sort_radio_main")
            df_show = st.session_state.df_proc if sort_option=="Padrão" else st.session_state.df_proc.sort_values(by=sort_option, kind='mergesort').reset_index(drop=True)
            st.dataframe(df_show, use_container_width=True)
            st.subheader("Exportar Resultados")
            t = datetime.now().strftime("%Y%m%d_%H%M%S")
            c1,c2 = st.columns(2)
            with c1: st.download_button("📥 Exportar para Excel", to_excel(df_show), f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument-spreadsheetml-sheet")
            with c2: st.download_button("📥 Exportar para CSV", df_show.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", mime="text/csv")

# Seção de Recursos no final
st.markdown("---")
col_auto, col_flex = st.columns(2)
with col_auto:
    with card_container():
        st.markdown(f"<h2>⚙️ Processamento Automático</h2>", unsafe_allow_html=True)
        st.write("Transformação automática dos dados conforme normas internas da empresa.")
with col_flex:
    with card_container():
        st.markdown(f"<h2>💾 Exportação Flexível</h2>", unsafe_allow_html=True)
        st.write("Exporte os dados processados em formatos CSV e Excel (XLSX).")
