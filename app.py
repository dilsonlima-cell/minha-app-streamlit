import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- NOVA PALETA DE CORES ---
COLOR_PALETTE = {
    "darkest_green": "#255000", # Verde muito escuro
    "dark_green": "#588100",    # Verde médio-escuro
    "medium_green": "#8db600",  # Verde médio-claro
    "light_green": "#c6da52",   # Verde pastel/claro
    "very_light_green": "#ffff8b", # Amarelo pastel/muito claro

    "white": "#FFFFFF",
    "black": "#000000",
    "gray_text": "#333333" # Um cinza escuro para texto em fundos claros
}


# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# Estilo CSS atualizado com base na nova paleta de cores
st.markdown(f"""
<style>
    /* Cor de fundo principal da aplicação */
    .stApp {{
        background-color: {COLOR_PALETTE["very_light_green"]}; /* Amarelo pastel/muito claro */
        color: {COLOR_PALETTE["darkest_green"]}; /* Texto padrão */
    }}

    /* Estilo para o cabeçalho superior */
    .header-bar {{
        background-color: {COLOR_PALETTE["darkest_green"]}; /* Verde muito escuro */
        padding: 10px 50px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        border-radius: 0px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    .header-bar h1 {{
        color: {COLOR_PALETTE["white"]}; /* Branco */
        margin: 0;
        font-size: 1.8rem;
        font-weight: 600;
    }}
    .header-bar .stMarkdown p {{
        color: {COLOR_PALETTE["light_green"]}; /* Verde pastel para o subtítulo */
        margin: 0;
        font-size: 0.9rem;
    }}
    .header-nav {{
        display: flex;
        gap: 20px;
    }}
    .header-nav .stMarkdown p {{
        color: {COLOR_PALETTE["medium_green"]}; /* Verde médio para links */
        cursor: pointer;
        transition: color 0.2s;
    }}
    .header-nav .stMarkdown p:hover {{
        color: {COLOR_PALETTE["white"]}; /* Branco no hover */
    }}

    /* Seção "Começar Processamento" */
    .start-processing-section {{
        background-color: {COLOR_PALETTE["medium_green"]}; /* Verde médio-claro */
        padding: 40px;
        text-align: center;
        border-radius: 10px;
        margin-bottom: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .start-processing-section h2 {{
        color: {COLOR_PALETTE["darkest_green"]}; /* Verde muito escuro */
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 10px;
    }}
    .start-processing-section p {{
        color: {COLOR_PALETTE["darkest_green"]};
        font-size: 1.1rem;
    }}

    /* Estilo para os cards de conteúdo */
    .card {{
        background-color: {COLOR_PALETTE["white"]};
        border: 1px solid {COLOR_PALETTE["light_green"]}; /* Borda verde pastel */
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }}

    /* TÍTULO PRINCIPAL (st.title) */
    h1 {{
        color: {COLOR_PALETTE["darkest_green"]};
        font-weight: 700;
        font-size: 2.5rem;
        padding-bottom: 0.3em;
    }}

    /* CABEÇALHOS (st.header) E SUB-CABEÇALHOS (st.subheader) */
    h2, h3 {{
        color: {COLOR_PALETTE["darkest_green"]};
        font-weight: 600;
        border: none;
        padding-bottom: 0px;
        margin-top: 0px;
    }}
    
    .card h2 {{
        margin-bottom: 1rem;
    }}

    /* Cor do texto principal dentro dos cards e outros elementos */
    body, p, label, .stMarkdown {{
        color: {COLOR_PALETTE["gray_text"]} !important; /* Cinza escuro para legibilidade em fundo claro */
    }}
    /* Sobrescreve para o texto no fundo principal */
    .stApp > header, .stApp > div:first-child > div:nth-child(2) > div.stMarkdown, .stApp > div:first-child > div:nth-child(2) > p {{
        color: {COLOR_PALETTE["darkest_green"]} !important;
    }}

    /* Estilo para os botões */
    .stButton>button {{
        background-color: {COLOR_PALETTE["dark_green"]}; /* Verde médio-escuro */
        color: {COLOR_PALETTE["white"]};
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 500;
        transition: background-color 0.2s;
    }}
    .stButton>button:hover {{
        background-color: {COLOR_PALETTE["darkest_green"]}; /* Verde mais escuro no hover */
        color: {COLOR_PALETTE["white"]};
    }}

    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {{
        background-color: {COLOR_PALETTE["light_green"]}; /* Verde pastel/claro */
        border-right: 1px solid {COLOR_PALETTE["dark_green"]};
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: {COLOR_PALETTE["darkest_green"]};
    }}
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {{
        color: {COLOR_PALETTE["gray_text"]} !important;
    }}

    /* Cor do texto do expander (Relatório de Processamento) */
    .st-emotion-cache-115fcme summary, .st-emotion-cache-115fcme button {{
        color: {COLOR_PALETTE["darkest_green"]} !important;
        font-weight: 600;
        font-size: 1.25rem;
    }}

    /* Cores do relatório */
    .stAlert[data-baseweb="alert"] > div {{
        border-radius: 8px;
    }}
    /* Cores de alerta padrão, ajustadas para melhor contraste na nova paleta */
    .stAlert.stAlert_success {{ background-color: #d4edda; color: #155724; border-color: #c3e6cb; }}
    .stAlert.stAlert_warning {{ background-color: #fff3cd; color: #856404; border-color: #ffeeba; }}
    .stAlert.stAlert_info {{ background-color: #d1ecf1; color: #0c5460; border-color: #bee5eb; }}
    .stAlert.stAlert_error {{ background-color: #f8d7da; color: #721c24; border-color: #f5c6cb; }}

    /* FORÇAR TEMA CLARO NA TABELA (DATAFRAME) */
    [data-testid="stDataFrame"] {{
        border: 1px solid {COLOR_PALETTE["light_green"]};
        border-radius: 8px;
    }}
    [data-testid="stDataFrame"] .col-header {{
        background-color: {COLOR_PALETTE["light_green"]} !important;
    }}
    [data-testid="stDataFrame"] .col-header-cell {{
        color: {COLOR_PALETTE["darkest_green"]} !important;
        font-weight: 600;
    }}
    [data-testid="stDataFrame"] .data-cell {{
        background-color: {COLOR_PALETTE["white"]} !important;
        color: {COLOR_PALETTE["gray_text"]} !important;
        border-color: {COLOR_PALETTE["light_green"]} !important;
    }}

    /* Campo de upload de arquivo no corpo principal */
    .upload-area-main .stFileUploader > div:first-child {{
        background-color: {COLOR_PALETTE["white"]};
        border: 2px dashed {COLOR_PALETTE["dark_green"]}; /* Borda tracejada verde médio */
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        color: {COLOR_PALETTE["gray_text"]};
    }}
    .upload-area-main .stFileUploader > div:first-child svg {{
        color: {COLOR_PALETTE["dark_green"]}; /* Ícone verde médio */
    }}

    /* Títulos dentro de cards */
    .card .st-emotion-cache-cnjvw7 h2, .card .st-emotion-cache-cnjvw7 h3 {{
        color: {COLOR_PALETTE["darkest_green"]};
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

# Layout da barra de cabeçalho (topo da página)
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


# Sidebar
with st.sidebar:
    st.header("Configurações")
    st.info("Utilize as opções abaixo para configurar o processamento.", icon="⚙️")
    state_file = st.text_input("Nome do arquivo de estado:", "estado_sequenciais.json", key="state_file_input")
    st.info("Salva os contadores sequenciais para evitar códigos duplicados.", icon="💾")


# Seção "Começar Processamento"
with st.container():
    st.markdown('<div class="start-processing-section">', unsafe_allow_html=True)
    st.header("Começar Processamento")
    st.write("Faça upload do arquivo TXT ou XLSX exportado do SolidWorks.")
    st.markdown('</div>', unsafe_allow_html=True)


# Main Content Area - Área de Upload de Arquivo BOM
with card_container():
    st.subheader("Upload de Arquivo BOM")
    st.write("Faça upload do arquivo TXT ou XLSX exportado do SolidWorks.")
    
    uploaded_file = st.file_uploader(
        "Clique ou arraste um arquivo",
        type=['txt','xlsx'],
        key="main_uploader",
        help="TXT deve ser separado por tabulação com cabeçalho na última linha."
    )
    # Adicionamos uma classe CSS para estilizar este uploader especificamente
    st.markdown('<div class="upload-area-main"></div>', unsafe_allow_html=True)


if not uploaded_file:
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
                        st.subheader("Detalhes do Processamento")
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

# Seção de "Recursos" (inferior)
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
