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
        # Retorna um SVG placeholder se a imagem não for encontrada
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
    .main-container {
        display: flex;
        flex-direction: row;
        gap: 20px;
    }
    .column {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }
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
    [data-testid="stFileUploader"] section {
        background-color: #256D7B; /* Verde Azulado */
        color: #fff;
    }
    [data-testid="stFileUploader"] label {
        font-weight: bold;
        color: #D4E157 !important; /* Cor com maior contraste */
        margin-bottom: 10px;
        display: block;
    }
    [data-testid="stFileUploader"] button {
        background-color: #333;
        color: #fff;
        border: 1px solid #555;
    }

    /* --- TABELA DE GRUPOS --- */
    [data-testid="stNumberInput"] input {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 1px solid #555 !important;
        border-radius: 4px;
    }
    [data-testid="stNumberInput"] button {
        background-color: #444 !important;
        color: #fff !important;
        border: 1px solid #555 !important;
    }
    
    /* --- DATAFRAME --- */
    [data-testid="stDataFrame"] {
        background-color: #256D7B; /* Verde Azulado */
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] table {
        color: #E0E0E0;
    }
    [data-testid="stDataFrame"] thead th {
        background-color: #1A4A53; /* Tom mais escuro de Verde Azulado */
        color: #D4E157;
        font-weight: bold;
        border-bottom: 2px solid #D4E157;
    }
    [data-testid="stDataFrame"] tbody tr:nth-of-type(even) {
        background-color: #2F7C8A; /* Tom mais claro de Verde Azulado */
    }
    [data-testid="stDataFrame"] tbody tr:nth-of-type(odd) {
        background-color: #256D7B; /* Verde Azulado */
    }
    [data-testid="stDataFrame"] tbody tr:hover td {
        background-color: #404040;
    }
    [data-testid="stDataFrame"] tbody td {
        border-color: #333;
    }

    /* --- RELATÓRIO --- */
    .report-item-success, .report-item-info, .report-item-warning, .report-item-error {
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 5px;
        border-left: 5px solid;
    }
    .report-item-success { background-color: #E6F3D8; border-color: #6E9B44; }
    .report-item-info { background-color: #E0F2F7; border-color: #007B9E; }
    .report-item-warning { background-color: #FFF3CD; border-color: #FFAA00; }
    .report-item-error { background-color: #F8D7DA; border-color: #D9534F; }
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
            content = [line for line in content if line.strip()]  # Remove linhas vazias
            if not content:
                return None, [], "Arquivo TXT vazio."
            
            # Tenta detectar o cabeçalho (assume que é a linha com mais colunas)
            header_candidates = [line.split('\t') for line in content]
            header_index = max(range(len(header_candidates)), key=lambda i: len(header_candidates[i]))
            header = [h.strip() for h in header_candidates[header_index]]
            
            if not header:
                return None, [], "Nenhum cabeçalho válido encontrado no arquivo TXT."
            
            data_lines = [line.split('\t') for line in content[:header_index] + content[header_index+1:]]
            parsed_data = [
                (line + [''] * len(header))[:len(header)]
                for line in data_lines if line
            ]
            df = pd.DataFrame(parsed_data, columns=header)
            df = df.iloc[::-1].reset_index(drop=True)  # Mantém a inversão, se necessário
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
    except UnicodeDecodeError:
        return None, [], "Erro de codificação: o arquivo TXT deve estar em UTF-8."
    except Exception as e:
        return None, [], f"Erro ao ler o arquivo: {str(e)}"

# --- process logic ---
def process_codes(df, sequentials, json_state, column_report):
    if df is None or df.empty:
        return pd.DataFrame(), [], "DataFrame vazio."

    report_log = list(column_report)
    report_log.append("--- Início do Processamento de Códigos ---")

    if 'PROCESSO' not in df.columns or df.empty:
        report_log.append("❌ Erro: DataFrame vazio ou coluna 'PROCESSO' ausente.")
        return pd.DataFrame(), report_log

    for g in list(sequentials.keys()):
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')

    # <<<--- CORREÇÃO APLICADA AQUI ---<<<
    df['PROCESSO'] = df['PROCESSO'].astype(str).str.strip().str.upper()
    
    linhas_vazias = df['PROCESSO'].isin(['', 'NAN', None]) | pd.isna(df['PROCESSO'])
    
    count_preenchido = 0
    for i in df[linhas_vazias].index:
        is_manufactured = manufactured_pattern.match(str(df.loc[i, 'Nº DA PEÇA']))
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if is_manufactured else 'COMERCIAL'
        count_preenchido += 1
    
    if count_preenchido > 0:
        report_log.append(f"✔️ Coluna 'PROCESSO' preenchida para **{count_preenchido}** itens.")

    df['CÓDIGO FINAL'] = 'NULO'
    
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA',''))
        m = commercial_pattern.match(num)
        if m:
            try:
                group, seq_str = num.split('-')
                sequentials[group] = max(sequentials.get(group, 0), int(seq_str))
            except: continue

    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue

        num = str(row.get('Nº DA PEÇA',''))
        m_direct = commercial_pattern.match(num)
        if m_direct and len(m_direct.group(1)) == 6:
            df.loc[i, 'CÓDIGO FINAL'] = num
            continue

        m = group_pattern.search(str(row.get('GRUPO DE PRODUTO','')))
        if m:
            g = m.group(1)
            next_code = int(sequentials.get(g, 0)) + 1
            while f"{g}-{next_code:06d}" in df['CÓDIGO FINAL'].values:
                next_code += 1
            if next_code > MAX_SEQ:
                report_log.append(f"❌ Limite de 6 dígitos atingido para o grupo {g}. Código mantido como NULO.")
                df.loc[i, 'CÓDIGO FINAL'] = 'NULO'
                continue
            
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
            report_log.append(f"✔️ '{row.get('TÍTULO','')}' recebeu o código: {new_code}")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO','')}' COMERCIAL sem grupo -> NULO")

    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()
    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts.pop()
            parent = '.'.join(parts)
            if parent in code_map: return code_map[parent]
        return ""
    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(find_parent_code)

    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    save_sequentials({k:int(v) for k,v in sequentials.items()})
    report_log.append("💾 Sequenciais atualizados no arquivo estado_sequenciais.json")

    num_codes_generated = len([l for l in report_log if l.startswith("✔️ '")])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- Interface ---

# --- HEADER ---
header_cols = st.columns([1, 4])
with header_cols[0]:
    st.markdown(f'<div class="header-container"><img src="{logo_base64}" alt="Logo Preciso"></div>', unsafe_allow_html=True)
with header_cols[1]:
    st.markdown('<div class="header-container"><h1>SolidWorks BOM Processor</h1><p>PROCESSAMENTO AUTOMÁTICO DE LISTAS DE MATERIAIS EXPORTADAS DO SOLIDWORKS</p></div>', unsafe_allow_html=True)

st.write("---")

# --- MAIN LAYOUT ---
col1, col2 = st.columns([1, 1.2])

with col1:
    with st.container():
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
        t_cols[2].markdown("**Próximo Código**")
        
        for g, desc in group_table.items():
            g_cols = st.columns([1, 2, 2])
            g_cols[0].write(g)
            g_cols[1].write(desc)
            key = f"seq_{g}_v{version}"
            init_val = int(st.session_state.get(key, json_state.get(g, 0)))
            g_cols[2].number_input(
                f"Próximo código {g}", 
                min_value=0, 
                max_value=MAX_SEQ, 
                value=init_val, 
                step=1, 
                key=key, 
                label_visibility="collapsed",
                help=f"Digite o próximo código para o grupo {g}. Deve ser um número entre 0 e {MAX_SEQ}."
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Começar Processamento")
        st.write("Configure os grupos acima e clique em Processar.")

        def increment_version():
            st.session_state["version"] += 1
        
        b_cols = st.columns(2)
        with b_cols[0]:
            st.markdown('<div class="btn-process">', unsafe_allow_html=True)
            process_clicked = st.button("Processar", help="Inicia o processamento do arquivo carregado")
            st.markdown('</div>', unsafe_allow_html=True)
        with b_cols[1]:
            st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
            if st.button("Resetar Inputs (Limpar)", on_click=increment_version, help="Limpa os campos de 'Próximo Código' para os valores salvos"):
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        
    if "last_report" in st.session_state:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Relatório de Processamento")
            for log in st.session_state["last_report"]:
                if log.startswith("✔️") or log.startswith("✅"): 
                    st.markdown(f'<div class="report-item-success">{log}</div>', unsafe_allow_html=True)
                elif log.startswith("⚠️"): 
                    st.markdown(f'<div class="report-item-warning">{log}</div>', unsafe_allow_html=True)
                elif log.startswith("❌"): 
                    st.markdown(f'<div class="report-item-error">{log}</div>', unsafe_allow_html=True)
                else: 
                    st.markdown(f'<div class="report-item-info">{log}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown('<div class="dark-card">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("1. Carregar Arquivo", type=['txt', 'xlsx'], help="Arraste e solte ou clique para selecionar o arquivo TXT ou XLSX exportado do SolidWorks")
        st.markdown('</div>', unsafe_allow_html=True)
    
    if "available_columns" in st.session_state:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("2. Selecionar Colunas para Exportar")
            st.session_state.selected_columns = st.multiselect(
                "Escolha as colunas que deseja incluir no arquivo final:",
                options=st.session_state.available_columns,
                default=st.session_state.get("selected_columns", st.session_state.available_columns)
            )
            st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Exportação")
        st.write("Os arquivos gravados ficam disponíveis para download abaixo após o processamento.")
        st.markdown('</div>', unsafe_allow_html=True)

    if "last_df_processed" in st.session_state:
        with st.container():
            st.markdown('<div class="dark-card">', unsafe_allow_html=True)
            st.subheader("Dados Processados")
            
            df_processed_full = pd.read_json(io.StringIO(st.session_state["last_df_processed"]), orient='split')
            selected_cols = st.session_state.get("selected_columns", df_processed_full.columns.tolist())
            valid_selected_cols = [col for col in selected_cols if col in df_processed_full.columns]
            df_final_display = df_processed_full[valid_selected_cols]

            st.dataframe(df_final_display, use_container_width=True)

            t = datetime.now().strftime("%Y%m%d_%H%M%S")
            dl_cols = st.columns(2)
            excel_data = to_excel(df_final_display)
            csv_data = df_final_display.to_csv(index=False).encode("utf-8")

            dl_cols[0].download_button("Baixar Excel (.xlsx)", excel_data, f"lista_codificada_{t}.xlsx")
            dl_cols[1].download_button("Baixar CSV (.csv)", csv_data, f"lista_codificada_{t}.csv")
            st.markdown('</div>', unsafe_allow_html=True)

# --- LÓGICA DE PROCESSAMENTO ---
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
                    st.session_state["available_columns"] = df_proc.columns.tolist()
                    
                    if "last_df_csv" in st.session_state: del st.session_state["last_df_csv"]
                    if "last_df_excel" in st.session_state: del st.session_state["last_df_excel"]

            st.success("Processamento concluído com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {str(e)}")
