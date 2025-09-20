import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
import base64

# --- CONFIGS ---
STATE_FILE = "estado_sequenciais.json"
MAX_SEQ = 999_999  # 6 dígitos máximo

# Colunas que o sistema espera e irá garantir que existam.
COLUNAS_OBRIGATORIAS = [
    'Nº DO ITEM', 'Nº DA PEÇA', 'TÍTULO', 'QTD.',
    'PROCESSO', 'GRUPO DE PRODUTO'
]

# --- Estilo (Baseado na imagem do novo layout) ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# Carregando a imagem do logo e convertendo para base64 para embutir no HTML
def get_image_as_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except IOError:
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iNTAiIHZpZXdCb3g9IjAgMCAyMDAgNTAiPgo8cGF0aCBmaWxsPSIjMDBBRUVGIiBkPSJNMjUsMEMxMS4xOSwwLDAsMTEuMTksMCwyNVMxMS4xOSw1MCwyNSw1MFM1MCwzOC44MSw1MCwyNVMyNSwwLDAsMjVaIE0yNSw0M0ExOCwxOCwwLDEsMSw0MywyNSwxOCwxOCwwLDAsMSwyNSw0M1oiLz4KPHRleHQgeD0iNjAiIHk9IjMzIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IiMzMzMiPlByZWNpc288L3RleHQ+Cjwvc3ZnPg=="

logo_base64 = get_image_as_base64("logo.png")

st.markdown("""
<style>
    /* --- GERAL --- */
    .stApp {
        background-color: #7E8C54; /* Verde Musgo */
        color: #333;
    }
    h1, h2, h3 {
        color: #FFFFFF !important;
    }
    .card h1, .card h2, .card h3 {
        color: #2D2D2D !important; /* Mantém a cor escura dentro dos cards brancos */
    }

    /* --- BOTÕES --- */
    .stButton > button {
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s ease-in-out;
    }

    /* --- CONTAINERS E CARDS --- */
    .card {
        background-color: #FFFFFF;
        border-radius: 8px;
        padding: 25px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .dark-card {
        background-color: #256D7B; /* Verde Azulado */
        border-radius: 8px;
        padding: 25px;
        color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .dark-card h3 {
        color: #FFFFFF !important;
    }

    /* --- HEADER --- */
    .header-container img {
        max-height: 50px;
    }
    .header-container h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
        color: #FFFFFF !important;
    }
    .header-container p {
        font-size: 1rem;
        color: #E0E0E0;
        margin: 0;
    }

    /* --- UPLOADER DE ARQUIVO --- */
    [data-testid="stFileUploader"] {
        background-color: #256D7B; /* Verde Azulado */
        border: 2px dashed #4E8A96;
        border-radius: 8px;
        padding: 20px;
    }
    [data-testid="stFileUploader"] label {
        color: #D4E157 !important; /* Cor com maior contraste */
    }

    /* --- DATAFRAME --- */
    [data-testid="stDataFrame"] thead th {
        background-color: #1A4A53; /* Tom mais escuro de Verde Azulado */
        color: #D4E157;
    }
</style>
""", unsafe_allow_html=True)

# --- JSON helpers ---
def load_sequentials(file_path=STATE_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sequentials(data, file_path=STATE_FILE):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- load file helper ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, [], "Nenhum arquivo carregado."
    
    report_log = []
    df = None
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif name.endswith(".txt"):
            content = uploaded_file.getvalue().decode('utf-8').splitlines()
            content = [line for line in content if line.strip()]
            if not content:
                return None, [], "Arquivo TXT vazio."
            
            header_candidates = [line.split('\t') for line in content]
            header_index = max(range(len(header_candidates)), key=lambda i: len(header_candidates[i]))
            header = [h.strip() for h in header_candidates[header_index]]
            
            if not header:
                return None, [], "Nenhum cabeçalho válido encontrado no arquivo TXT."
            
            data_lines = [line.split('\t') for line in content[:header_index] + content[header_index+1:]]
            parsed_data = [(line + [''] * len(header))[:len(header)] for line in data_lines if line]
            df = pd.DataFrame(parsed_data, columns=header)
            df = df.iloc[::-1].reset_index(drop=True)
        else:
            return None, [], "Formato de arquivo não suportado."

        colunas_originais = set(df.columns)
        colunas_obrigatorias_set = set(COLUNAS_OBRIGATORIAS)
        colunas_ausentes = colunas_obrigatorias_set - colunas_originais
        if colunas_ausentes:
            report_log.append(f"⚠️ Colunas ausentes (criadas vazias): **{', '.join(sorted(list(colunas_ausentes)))}**")
            for col in sorted(list(colunas_ausentes)):
                df[col] = ''

        ordem_final = COLUNAS_OBRIGATORIAS + sorted(list(colunas_originais - colunas_obrigatorias_set))
        df = df[ordem_final]
        df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)
        
        return df, report_log, "Arquivo lido com sucesso."
    except Exception as e:
        return None, [], f"Erro ao ler o arquivo: {str(e)}"

# --- LÓGICA DE PROCESSAMENTO (REATORADA) ---

def fill_process_column(df, report_log):
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    df['PROCESSO'] = df['PROCESSO'].astype(str).str.strip().str.upper()
    
    linhas_vazias = df['PROCESSO'].isin(['', 'NAN', 'NONE']) | pd.isna(df['PROCESSO'])
    count_preenchido = 0
    
    for i in df[linhas_vazias].index:
        is_manufactured = manufactured_pattern.match(str(df.loc[i, 'Nº DA PEÇA']))
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if is_manufactured else 'COMERCIAL'
        count_preenchido += 1
    
    if count_preenchido > 0:
        report_log.append(f"✔️ Coluna 'PROCESSO' preenchida para **{count_preenchido}** itens.")
    return df

def update_sequentials_from_existing(df, sequentials):
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA', ''))
        m = commercial_pattern.match(num)
        if m:
            try:
                group, seq_str = num.split('-')
                sequentials[group] = max(sequentials.get(group, 0), int(seq_str))
            except (ValueError, KeyError):
                continue
    return sequentials

def generate_new_codes(df, sequentials, report_log):
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')
    group_pattern = re.compile(r'(\d{3})')
    
    df['CÓDIGO FINAL'] = 'NULO'
    
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue

        num = str(row.get('Nº DA PEÇA', ''))
        m_direct = commercial_pattern.match(num)
        if m_direct and len(m_direct.group(1)) == 6:
            df.loc[i, 'CÓDIGO FINAL'] = num
            continue

        m_group = group_pattern.search(str(row.get('GRUPO DE PRODUTO', '')))
        if m_group:
            g = m_group.group(1)
            next_code = int(sequentials.get(g, 0)) + 1
            while f"{g}-{next_code:06d}" in df['CÓDIGO FINAL'].values:
                next_code += 1
            
            if next_code > MAX_SEQ:
                report_log.append(f"❌ Limite de 6 dígitos atingido para o grupo {g}. Código mantido como NULO.")
                continue
            
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
            report_log.append(f"✔️ '{row.get('TÍTULO', '')}' recebeu o código: {new_code}")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO', '')}' COMERCIAL sem grupo -> NULO")
    
    return df, sequentials

def create_parent_codes(df):
    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM'].astype(str)).to_dict()
    
    def find_parent_code(item_id):
        parts = str(item_id).split('.')
        while len(parts) > 1:
            parts.pop()
            parent = '.'.join(parts)
            if parent in code_map:
                return code_map[parent]
        return ""
    
    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(find_parent_code)
    return df

def sort_and_format_dataframe(df):
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO', 'CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.upper()
        
    return df

def process_codes(df, sequentials, json_state, column_report):
    if df is None or df.empty:
        return pd.DataFrame(), ["DataFrame vazio."]

    if 'PROCESSO' not in df.columns:
        return df, ["❌ Erro: Coluna 'PROCESSO' ausente."]
    
    report_log = list(column_report)
    report_log.append("--- Início do Processamento de Códigos ---")
    
    # Atualiza sequenciais da interface com os do arquivo JSON
    for g in sequentials.keys():
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    # Etapa 1: Preencher coluna PROCESSO
    df = fill_process_column(df, report_log)
    
    # Etapa 2: Ler códigos existentes para atualizar sequenciais
    sequentials = update_sequentials_from_existing(df, sequentials)
    
    # Etapa 3: Gerar novos códigos
    df, sequentials = generate_new_codes(df, sequentials, report_log)
    
    # Etapa 4: Criar códigos pai
    df = create_parent_codes(df)
    
    # Etapa 5: Ordenar e formatar
    df = sort_and_format_dataframe(df)

    # Salvar estado
    save_sequentials({k: int(v) for k, v in sequentials.items()})
    report_log.append("💾 Sequenciais atualizados no arquivo estado_sequenciais.json")

    num_codes_generated = len([l for l in report_log if "recebeu o código" in l])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    
    return df, report_log

# --- UTILITIES ---

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- INTERFACE ---

# HEADER
st.markdown(f'<div class="header-container" style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px;"><img src="data:image/png;base64,{logo_base64}" alt="Logo"><div><h1>SolidWorks BOM Processor</h1><p>PROCESSAMENTO AUTOMÁTICO DE LISTAS DE MATERIAIS</p></div></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1.2])

with col1:
    with st.container(border=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Tabela de Grupos – Próximo Código")
        
        group_table = {
            "100": "Mecânico", "200": "Elétrico", "300": "Hidráulico Água",
            "400": "Hidráulico Óleo", "500": "Pneumático", "600": "Tecnologia",
            "700": "Infraestrutura", "800": "Insumos", "900": "Segurança", "950": "Serviço"
        }
        json_state = load_sequentials()
        if "version" not in st.session_state: st.session_state["version"] = 0
        version = int(st.session_state["version"])

        t_cols = st.columns([1, 2, 2])
        t_cols[0].markdown("**Grupo**")
        t_cols[1].markdown("**Descrição**")
        t_cols[2].markdown("**Próximo Seq.**")
        
        for g, desc in group_table.items():
            g_cols = st.columns([1, 2, 2])
            g_cols[0].write(g)
            g_cols[1].write(desc)
            key = f"seq_{g}_v{version}"
            init_val = int(st.session_state.get(key, json_state.get(g, 0)))
            g_cols[2].number_input(f"seq_{g}", value=init_val, min_value=0, max_value=MAX_SEQ, step=1, key=key, label_visibility="collapsed")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    with st.container(border=False):
        st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
        st.subheader("Começar Processamento")
        
        def increment_version():
            st.session_state["version"] += 1
        
        b_cols = st.columns(2)
        process_clicked = b_cols[0].button("Processar", use_container_width=True)
        if b_cols[1].button("Resetar Inputs (Limpar)", on_click=increment_version, use_container_width=True):
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        
    if "last_report" in st.session_state:
        with st.container(border=False):
            st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
            st.subheader("Relatório de Processamento")
            st.text_area("Log", "".join(log + "\n" for log in st.session_state["last_report"]), height=250)
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    with st.container(border=False):
        st.markdown('<div class="dark-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("1. Carregar Arquivo", type=['txt', 'xlsx'])
        st.markdown('</div>', unsafe_allow_html=True)
    
    if "last_df_processed" in st.session_state:
        st.markdown('<div class="dark-card" style="margin-top: 20px;">', unsafe_allow_html=True)
        st.subheader("Dados Processados")
        
        df_processed_full = pd.read_json(io.StringIO(st.session_state["last_df_processed"]), orient='split')
        st.dataframe(df_processed_full, use_container_width=True)

        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_data = to_excel(df_processed_full)

        dl_cols = st.columns(2)
        dl_cols[0].download_button("Baixar Excel (.xlsx)", excel_data, f"lista_codificada_{t}.xlsx", use_container_width=True)
        dl_cols[1].download_button("Baixar CSV (.csv)", df_processed_full.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- LÓGICA DE EXECUÇÃO ---
if process_clicked:
    if uploaded_file is None:
        st.error("Por favor, carregue um arquivo antes de processar.")
    else:
        sequentials = {g: int(st.session_state.get(f"seq_{g}_v{version}", 0)) for g in group_table.keys()}
        try:
            with st.spinner("Processando... Por favor, aguarde."):
                df_raw, column_report, msg = load_data(uploaded_file)
                if df_raw is None:
                    st.error(msg)
                else:
                    df_proc, report = process_codes(df_raw.copy(), sequentials, json_state, column_report)
                    st.session_state["last_report"] = report
                    st.session_state["last_df_processed"] = df_proc.to_json(orient='split', date_format='iso')
            st.success("Processamento concluído!")
            st.rerun()
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: '{e}'")
