import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- PALETA DE CORES ---
# Baseado na Image 2:
COLOR_PALETTE = {
    "light_green": "#88B257", # Mais claro
    "medium_green": "#4A701C", # Médio
    "dark_green": "#284703",  # Mais escuro, para textos importantes/background de destaque
    "dark_gray": "#434D36",   # Cinza escuro, para texto principal
    "medium_gray": "#555D4C", # Cinza médio, para texto secundário
    "white": "#FFFFFF",
    "off_white": "#F8F9FA", # Fundo geral, um cinza muito claro
    "light_gray_border": "#dee2e6", # Borda para cards/tabelas
    "light_bg_sidebar": "#e9ecef", # Fundo da sidebar
    "button_hover": "#3C5A18" # Um verde ligeiramente mais escuro para hover
}


# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# Estilo CSS atualizado com base na nova paleta de cores e layout da Image 1
st.markdown(f"""
<style>
    /* Cor de fundo principal */
    .stApp {{
        background-color: {COLOR_PALETTE["off_white"]}; /* Cinza muito claro */
        color: {COLOR_PALETTE["dark_gray"]}; /* Texto padrão */
    }}

    /* Estilo para o cabeçalho superior (semelhante ao da Image 1) */
    .header-bar {{
        background-color: {COLOR_PALETTE["dark_green"]}; /* Verde escuro */
        padding: 10px 50px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-radius: 0px; /* Borda reta */
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .header-bar h1 {{
        color: {COLOR_PALETTE["white"]}; /* Branco */
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }}
    .header-bar .stMarkdown p {{
        color: {COLOR_PALETTE["white"]}; /* Branco */
        margin: 0;
        font-size: 0.9rem;
    }}
    .header-nav {{
        display: flex;
        gap: 20px;
    }}
    .header-nav .stMarkdown p {{
        color: {COLOR_PALETTE["light_green"]}; /* Verde claro para links */
        cursor: pointer;
        transition: color 0.2s;
    }}
    .header-nav .stMarkdown p:hover {{
        color: {COLOR_PALETTE["white"]}; /* Branco no hover */
    }}

    /* Seção "Começar Processamento" (amarela na Image 1) */
    .start-processing-section {{
        background-color: {COLOR_PALETTE["light_green"]}; /* Verde claro */
        padding: 40px;
        text-align: center;
        border-radius: 10px;
        margin-bottom: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .start-processing-section h2 {{
        color: {COLOR_PALETTE["dark_green"]}; /* Verde escuro */
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 10px;
    }}
    .start-processing-section p {{
        color: {COLOR_PALETTE["dark_gray"]}; /* Cinza escuro */
        font-size: 1.1rem;
    }}

    /* Estilo para os cards de conteúdo */
    .card {{
        background-color: {COLOR_PALETTE["white"]};
        border: 1px solid {COLOR_PALETTE["light_gray_border"]};
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }}

    /* TÍTULO PRINCIPAL (st.title) - Corrigido para seções dentro de cards, se houver */
    h1 {{
        color: {COLOR_PALETTE["dark_green"]}; /* Verde corporativo escuro */
        font-weight: 700;
        font-size: 2.5rem;
        padding-bottom: 0.3em;
    }}

    /* CABEÇALHOS (st.header) E SUB-CABEÇALHOS (st.subheader) */
    h2, h3 {{
        color: {COLOR_PALETTE["dark_green"]}; /* Verde corporativo escuro */
        font-weight: 600;
        border: none;
        padding-bottom: 0px;
        margin-top: 0px;
    }}
    
    .card h2 {{
        margin-bottom: 1rem;
    }}

    /* Cor do texto principal */
    body, p, label, .stMarkdown {{
        color: {COLOR_PALETTE["dark_gray"]} !important; /* Texto cinza escuro */
    }}
    
    /* Estilo para os botões */
    .stButton>button {{
        background-color: {COLOR_PALETTE["medium_green"]}; /* Verde médio */
        color: {COLOR_PALETTE["white"]};
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 500;
        transition: background-color 0.2s;
    }}
    .stButton>button:hover {{
        background-color: {COLOR_PALETTE["button_hover"]}; /* Tom mais escuro no hover */
        color: {COLOR_PALETTE["white"]};
    }}

    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {{
        background-color: {COLOR_PALETTE["light_bg_sidebar"]}; /* Cinza claro */
        border-right: 1px solid {COLOR_PALETTE["light_gray_border"]};
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {COLOR_PALETTE["dark_green"]};
    }}
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {{
        color: {COLOR_PALETTE["dark_gray"]} !important; /* Texto escuro para contraste */
    }}

    /* Cor do texto do expander (Relatório de Processamento) */
    .st-emotion-cache-115fcme summary, .st-emotion-cache-115fcme button {{ /* Ajuste para o novo identificador do expander */
        color: {COLOR_PALETTE["dark_green"]} !important;
        font-weight: 600;
        font-size: 1.25rem;
    }}

    /* Cores do relatório */
    .stAlert[data-baseweb="alert"] > div {{
        border-radius: 8px;
    }}
    .stAlert.stAlert_success {{ background-color: #e6ffed; color: #1f874b; border-color: #1f874b; }}
    .stAlert.stAlert_warning {{ background-color: #fff3e6; color: #cc7000; border-color: #cc7000; }}
    .stAlert.stAlert_info {{ background-color: #e6f7ff; color: #007bff; border-color: #007bff; }}
    .stAlert.stAlert_error {{ background-color: #ffe6e6; color: #cc0000; border-color: #cc0000; }}


    /* FORÇAR TEMA CLARO NA TABELA (DATAFRAME) */
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLOR_PALETTE["light_gray_border"]};
        border-radius: 8px;
    }}
    [data-testid="stDataFrame"] .col-header {{
        background-color: {COLOR_PALETTE["light_bg_sidebar"]} !important; /* Cinza claro */
    }}
    [data-testid="stDataFrame"] .col-header-cell {{
        color: {COLOR_PALETTE["dark_gray"]} !important;
        font-weight: 600;
    }}
    [data-testid="stDataFrame"] .data-cell {{
        background-color: {COLOR_PALETTE["white"]} !important;
        color: {COLOR_PALETTE["dark_gray"]} !important;
        border-color: {COLOR_PALETTE["light_gray_border"]} !important;
    }}

    /* Campo de upload de arquivo */
    .st-emotion-cache-1j0r50e {{ /* Target the file uploader wrapper */
        background-color: {COLOR_PALETTE["white"]};
        border: 2px dashed {COLOR_PALETTE["medium_green"]}; /* Borda tracejada verde */
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        color: {COLOR_PALETTE["dark_gray"]};
    }}
    .st-emotion-cache-1j0r50e svg {{
        color: {COLOR_PALETTE["medium_green"]}; /* Ícone verde */
    }}

    /* Títulos dentro de cards, como "Upload de Arquivo BOM" */
    .card .st-emotion-cache-cnjvw7 h2 {{ /* Target specific h2 within card */
        color: {COLOR_PALETTE["dark_green"]};
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 15px;
    }}

    /* Para o st.radio horizontal */
    .st-emotion-cache-j9xjqf {{
        gap: 20px;
    }}

</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO AUXILIAR PARA CARD ---
@contextmanager
def card_container():
    """Cria um container com a classe CSS 'card'."""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)


# --- FUNÇÕES AUXILIARES (AS SUAS FUNÇÕES ORIGINAIS) ---

def load_sequentials(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sequentials(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

@st.cache_data
def load_data(uploaded_file):
    """Lê TXT (tabulado) ou XLSX e converte para DataFrame."""
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."

    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            # Garante que colunas essenciais existam
            for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
                if col not in df.columns:
                    df[col] = ''
            return df, "Arquivo XLSX lido com sucesso."

        # Leitura de TXT (mesma lógica anterior, mas mais tolerante)
        content = uploaded_file.getvalue().decode('utf-8').splitlines()
        header_line_index = -1
        for i in range(len(content) - 1, -1, -1):
            if content[i].strip():
                header_line_index = i
                break

        if header_line_index == -1:
            return None, "Não foi possível encontrar o cabeçalho no TXT."

        header = [h.strip() for h in content[header_line_index].split('\t')]
        data_lines = content[:header_line_index]

        parsed_data = []
        for line in data_lines:
            if line.strip():
                cells = [cell.strip() for cell in line.split('\t')]
                while len(cells) < len(header):
                    cells.append('')
                parsed_data.append(cells[:len(header)])
            
        df = pd.DataFrame(parsed_data, columns=header)
        df = df.iloc[::-1].reset_index(drop=True) # Inverte a ordem para o TXT, se necessário

        for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
            if col not in df.columns:
                df[col] = ''

        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)

        return df, "Arquivo TXT lido com sucesso."
    except Exception as e:
        return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df, state_file):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    sequentials = load_sequentials(state_file)
    report_log.append(f"{'💾' if sequentials else 'ℹ️'} Estado sequenciais carregado: {sequentials or 'Nenhum'}")

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{4}$')

    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # Ajusta sequenciais iniciais
    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA'])
        if commercial_pattern.match(num):
            try:
                group, seq = num.split('-')
                seq = int(seq)
                if group not in sequentials or seq > sequentials[group]:
                    sequentials[group] = seq
            except:
                continue
    report_log.append(f"Sequenciais iniciais: {sequentials or 'Nenhum'}")

    # Geração de códigos
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
                report_log.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                report_log.append(f"⚠️ '{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

    # Hierarquia pai-filho (corrigida)
    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()

    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts = parts[:-1]
            parent = '.'.join(parts)
            if parent in code_map:
                return code_map[parent]
        return None

    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(lambda x: find_parent_code(x) or "")
    report_log.append("Hierarquia pai-filho processada.")
    
    # Reordenar colunas
    cols = df.columns.tolist()
    if 'CÓDIGO PAI' in cols:
        cols.pop(cols.index('CÓDIGO PAI'))
        if 'CÓDIGO FINAL' in cols:
            final_code_index = cols.index('CÓDIGO FINAL')
            cols.insert(final_code_index + 1, 'CÓDIGO PAI')
            df = df[cols]


    # Ordenação lógica
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)

    # Padronizar strings
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    save_sequentials(state_file, sequentials)
    report_log.append(f"💾 Sequenciais salvos em {state_file}")
    
    num_codes_generated = len([log for log in report_log if '✔️' in log])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")

    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    processed_data = out.getvalue()
    return processed_data

# --- INTERFACE ---

# Layout da barra de cabeçalho (topo da página, como na Image 1)
st.markdown(f"""
<div class="header-bar">
    <div>
        <h1>SolidWorks BOM Processor</h1>
        <p>Processamento automático de listas de materiais exportadas do SolidWorks</p>
    </div>
    <div class="header-nav">
        <p>⚡ Processamento Rápido</p>
        <p>📝 Normas Internas</p>
        <p>💾 Export Excel/CSV</p>
    </div>
</div>
""", unsafe_allow_html=True)


# Sidebar - Mantida com as suas opções originais
with st.sidebar:
    st.header("1. Carregar Arquivo")
    st.info("TXT deve ser separado por tabulação com cabeçalho na última linha.", icon="ℹ️")
    uploaded_file = st.file_uploader("Selecione arquivo TXT ou XLSX", type=['txt','xlsx'], key="sidebar_uploader")
    
    st.header("2. Persistência de Códigos")
    state_file = st.text_input("Nome do arquivo de estado:", "estado_sequenciais.json", key="state_file_input")
    st.info("Salva os contadores sequenciais para evitar códigos duplicados.", icon="💾")
    
    # Adicionar uma imagem na sidebar para preencher, se desejar (removi a do unsplash por ser genérica)
    # st.image("caminho/para/sua/logo.png", use_column_width='auto')


# Seção "Começar Processamento" (similar ao bloco amarelo da Image 1)
with st.container():
    st.markdown('<div class="start-processing-section">', unsafe_allow_html=True)
    st.header("Começar Processamento")
    st.write("Faça upload do arquivo TXT exportado do SolidWorks ou use dados de exemplo.")
    st.markdown('</div>', unsafe_allow_html=True)


# Main Content Area
if not uploaded_file:
    with card_container():
        st.subheader("Upload de Arquivo BOM")
        st.write("Faça upload do arquivo TXT ou CSV exportado do SolidWorks")
        
        # Um placeholder visual para o uploader
        st.markdown(f"""
        <div style="
            border: 2px dashed {COLOR_PALETTE["medium_green"]};
            border-radius: 10px;
            padding: 30px;
            text-align: center;
            color: {COLOR_PALETTE["dark_gray"]};
            margin-top: 20px;
        ">
            <p style="font-size: 3rem; margin-bottom: 10px;">📄</p>
            <p>Clique ou arraste um arquivo</p>
            <p style="font-size: 0.8rem; color: {COLOR_PALETTE["medium_gray"]};">Suporte para arquivos .txt e .xlsx (máx. 5MB)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Para carregar dados de exemplo (se você tiver essa funcionalidade)
        # if st.button("Carregar Dados de Exemplo", key="load_example_data"):
        #     st.session_state["uploaded_file"] = "exemplo.txt" # Ou carregar um DF de exemplo
        #     st.rerun() # Para reprocessar com o "arquivo" de exemplo

    st.info("Aguardando upload de um arquivo para começar...", icon="👆")
else:
    try:
        with st.spinner("Processando..."):
            df_raw, msg = load_data(uploaded_file)
            if df_raw is None:
                st.error(f"❌ {msg}")
            else:
                df_proc, report = process_codes(df_raw.copy(), state_file)

                # Usando as abas para organizar Relatório e Tabela
                tab_relatorio, tab_dados = st.tabs(["📄 Relatório de Processamento", "📊 Lista de Peças Atualizada"])

                with tab_relatorio:
                    with card_container():
                        st.subheader("Detalhes do Processamento") # Título dentro do card
                        for log in report:
                            if "✔️" in log or "✅" in log: st.success(log)
                            elif "⚠️" in log: st.warning(log)
                            else: st.info(log)
                            

                with tab_dados:
                    with card_container():
                        st.subheader("Dados Processados")
                        sort_option = st.radio("Classificar por:", ("Padrão","GRUPO DE PRODUTO","PROCESSO"), horizontal=True, key="sort_radio_main")
                        df_show = df_proc if sort_option=="Padrão" else df_proc.sort_values(by=sort_option, kind='mergesort').reset_index(drop=True)
                        st.dataframe(df_show, use_container_width=True)

                        st.subheader("Exportar Resultados")
                        t = datetime.now().strftime("%Y%m%d_%H%M%S")
                        c1,c2 = st.columns(2)
                        with c1:
                            st.download_button("📥 Exportar para Excel", to_excel(df_show), f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        with c2:
                            st.download_button("📥 Exportar para CSV", df_show.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

# Seção de "Recursos" (inferior, como na Image 1)
st.markdown("---") # Linha separadora
col_auto, col_flex = st.columns(2)
with col_auto:
    with card_container():
        st.markdown(f"<h2>⚙️ Processamento Automático</h2>", unsafe_allow_html=True)
        st.write("Transformação automática dos dados conforme normas internas da empresa.")
with col_flex:
    with card_container():
        st.markdown(f"<h2>💾 Exportação Flexível</h2>", unsafe_allow_html=True)
        st.write("Exporte os dados processados em formatos CSV e Excel (XLSX).")
