import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
import math

# --- CONFIGS ---
STATE_FILE = "estado_sequenciais.json"
MAX_SEQ = 999_999

COLUNAS_OBRIGATORIAS = [
    'Nº DO ITEM', 'Nº DA PEÇA', 'TÍTULO', 'QTD.',
    'PROCESSO', 'GRUPO DE PRODUTO'
]

# --- Estilo ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# Função para converter imagens para base64
def get_image_as_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except IOError:
        return None

# Carregando a imagem de fundo do novo cabeçalho
header_bg_base64 = get_image_as_base64("header_bg.jpg")

# SVG do ícone do cabeçalho
icon_svg = """
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" fill="currentColor" class="bi bi-file-earmark-spreadsheet-fill" viewBox="0 0 16 16">
  <path d="M6 12v-2h3v2H6z"/>
  <path d="M9.293 0H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V4.707A1 1 0 0 0 13.707 4L10 .293A1 1 0 0 0 9.293 0zM9.5 3.5v-2l3 3h-2a1 1 0 0 1-1-1zM3 9h10v1h-3v2h3v1h-3v2H9v-2H6v2H5v-2H3v-1h2v-2H3V9z"/>
</svg>
"""

header_style = ""
if header_bg_base64:
    header_style = f"""
        background-image: linear-gradient(rgba(90, 102, 61, 0.9), rgba(90, 102, 61, 0.9)), url(data:image/jpeg;base64,{header_bg_base64});
    """
else:
    header_style = "background: linear-gradient(45deg, #5a663d, #7E8C54);"

st.markdown(f"""
<style>
    /* GERAL */
    .stApp {{ background-color: #e5e9dc; }}
    h1, h2, h3 {{ color: #1a202c !important; }}

    /* CABEÇALHO */
    .banner-header {{ display: flex; align-items: center; gap: 20px; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; color: white; {header_style} background-size: cover; background-position: center; }}
    .banner-icon {{ background-color: #B3D10D; border-radius: 50%; width: 64px; height: 64px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
    .banner-icon svg {{ color: #2D2D2D; }}
    .banner-text h1 {{ font-size: 2.2rem; font-weight: 700; color: #FFFFFF !important; margin: 0; line-height: 1.2; }}
    .banner-text p {{ font-size: 1.1rem; color: rgba(255, 255, 255, 0.9) !important; margin: 0; }}

    /* --- NOVO: ESTILO DO FILE UPLOADER --- */
    .upload-box {{
        background-color: #256D7B;
        border-radius: 12px;
        padding: 1.5rem;
    }}
    .upload-box [data-testid="stFileUploader"] {{
        border: 2px dashed #4E8A96;
        border-radius: 8px;
    }}
    .upload-box [data-testid="stFileUploader"] section {{
        padding: 2rem 1rem;
        background-color: transparent;
        border: none;
    }}
    .upload-box [data-testid="stFileUploader"] button {{
        background-color: #B3D10D !important;
        color: #2D2D2D !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
    }}
    .upload-box [data-testid="stFileUploader"] small {{
        color: rgba(255, 255, 255, 0.8);
    }}
    .formatos-suportados {{
        text-align: left;
        margin-top: 1.5rem;
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
    }}
    .formatos-suportados strong {{ color: white; }}
    .formatos-suportados li {{ margin-left: 20px; }}

    /* Estilos dos outros componentes (sem alteração) */
    .stButton > button {{ border-radius: 8px; padding: 8px 20px; font-weight: 600; transition: all 0.2s ease-in-out; }}
    .stButton > button:hover {{ filter: brightness(1.1); }}
    .report-container {{ max-height: 400px; overflow-y: auto; padding-right: 10px; }}
    .report-item {{ display: flex; align-items: center; padding: 12px; margin-bottom: 8px; border-radius: 8px; border: 1px solid; }}
    .report-item-icon {{ display: flex; justify-content: center; align-items: center; min-width: 24px; height: 24px; border-radius: 50%; margin-right: 12px; font-weight: bold; color: white; }}
    .report-item-success {{ background-color: #e6f3d8; border-color: #c3d9a5; }}
    .report-item-success .report-item-icon {{ background-color: #6E9B44; }}
    .report-item-info {{ background-color: #e0f2f7; border-color: #a0c4d1; }}
    .report-item-info .report-item-icon {{ background-color: #007B9E; }}
    .report-item-warning {{ background-color: #fff3cd; border-color: #ffda77; }}
    .report-item-warning .report-item-icon {{ background-color: #FFAA00; }}
    .stDownloadButton > button {{ background-color: #B3D10D !important; color: #2D2D2D !important; font-size: 1.1rem !important; font-weight: 700 !important; padding: 1rem !important; border-radius: 12px !important; border: none !important; width: 100%; }}
    .stDownloadButton > button:hover {{ filter: brightness(1.05); color: #000 !important; }}
</style>
""", unsafe_allow_html=True)

# (O restante do código Python, incluindo as funções de processamento, permanece o mesmo)
# --- Funções auxiliares (sem alteração) ---
def load_sequentials(file_path=STATE_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_sequentials(data, file_path=STATE_FILE):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None: return None, [], "Nenhum arquivo carregado."
    report_log, df = [], None
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx"): df = pd.read_excel(uploaded_file)
        elif name.endswith(".txt"):
            content = uploaded_file.getvalue().decode('utf-8').splitlines()
            header = [h.strip() for h in content[-1].split('\t')]
            data_lines = [l for l in content[:-1] if l.strip()]
            parsed_data = [(line.split('\t') + [''] * len(header))[:len(header)] for line in data_lines]
            df = pd.DataFrame(parsed_data, columns=header).iloc[::-1].reset_index(drop=True)
        else: return None, [], "Formato de arquivo não suportado."
        missing_cols = set(COLUNAS_OBRIGATORIAS) - set(df.columns)
        if missing_cols:
            report_log.append(f"⚠️ Colunas ausentes (criadas vazias): **{', '.join(sorted(list(missing_cols)))}**")
            for col in sorted(list(missing_cols)): df[col] = ''
        final_order = COLUNAS_OBRIGATORIAS + sorted(list(set(df.columns) - set(COLUNAS_OBRIGATORIAS)))
        df = df[final_order]
        df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)
        return df, report_log, "Arquivo lido com sucesso."
    except Exception as e: return None, [], f"Erro ao ler o arquivo: {e}"

def process_codes(df, sequentials, json_state, column_report):
    if df is None or df.empty: return pd.DataFrame(), [], "DataFrame vazio."
    report_log = list(column_report)
    for g in sequentials.keys(): sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))
    group_pattern, manu_pattern, comm_pattern = re.compile(r'(\d{3})'), re.compile(r'^\d{2}-\d{4}-\d{4}-.*'), re.compile(r'^\d{3}-(\d+)$')
    df['PROCESSO'] = df['PROCESSO'].astype(str).str.strip().str.upper()
    empty_process = df['PROCESSO'].isin(['', 'NAN', None]) | pd.isna(df['PROCESSO'])
    count_filled = 0
    for i in df[empty_process].index:
        is_manu = manu_pattern.match(str(df.loc[i, 'Nº DA PEÇA']))
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if is_manu else 'COMERCIAL'
        count_filled += 1
    if count_filled > 0: report_log.append(f"✔️ Coluna 'PROCESSO' preenchida para {count_filled} itens.")
    df['CÓDIGO FINAL'] = 'NULO'
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA',''))
        if m := comm_pattern.match(num):
            try:
                group, seq_str = num.split('-')
                sequentials[group] = max(sequentials.get(group, 0), int(seq_str))
            except: continue
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue
        num = str(row.get('Nº DA PEÇA',''))
        if (m_direct := comm_pattern.match(num)) and len(m_direct.group(1)) == 6:
            df.loc[i, 'CÓDIGO FINAL'] = num
            continue
        if m := group_pattern.search(str(row.get('GRUPO DE PRODUTO',''))):
            g = m.group(1)
            next_code = sequentials.get(g, 0) + 1
            while f"{g}-{next_code:06d}" in df['CÓDIGO FINAL'].values: next_code += 1
            if next_code > MAX_SEQ: raise Exception(f"Limite de 6 dígitos atingido para o grupo {g}.")
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
        else: report_log.append(f"⚠️ \"{row.get('TÍTULO','')}\" COMERCIAL sem grupo -> NULO")
    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()
    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts.pop()
            if (parent := '.'.join(parts)) in code_map: return code_map[parent]
        return ""
    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(find_parent_code)
    df['TIPO'] = df.apply(lambda r: 1 if r['PROCESSO'] == 'FABRICADO' else 2 if r['CÓDIGO FINAL'] != 'NULO' else 3, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']): df[col] = df[col].astype(str).str.upper()
    save_sequentials({k:int(v) for k,v in sequentials.items()})
    num_codes = df['CÓDIGO FINAL'].ne(df['Nº DA PEÇA']).sum() - df['CÓDIGO FINAL'].eq('NULO').sum()
    report_log.insert(0, f"✅ Processamento concluído. {num_codes} novos códigos comerciais foram gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w: df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()
    
# --- Interface --- #

# Cabeçalho
st.markdown(f"""
<div class="banner-header">
    <div class="banner-icon">{icon_svg}</div>
    <div class="banner-text">
        <h1>SolidWorks BOM Processor</h1>
        <p>Processamento automático de listas de materiais exportadas do SolidWorks</p>
    </div>
</div>
""", unsafe_allow_html=True)


# Layout principal
col1, col2 = st.columns([5, 7])

# --- Coluna da Esquerda ---
with col1:
    with st.container(border=True):
        st.subheader("⚙️ Tabela de Grupos")
        group_table = { "100":"Mecânico", "200":"Elétrico", "300":"Hidráulico Água", "400":"Hidráulico Óleo", "500":"Pneumático", "600":"Tecnologia", "700":"Infraestrutura", "800":"Insumos", "900":"Segurança", "950":"Serviço" }
        json_state = load_sequentials()
        if "version" not in st.session_state: st.session_state["version"] = 0
        version = st.session_state["version"]
        t_cols = st.columns([1, 2, 2])
        t_cols[0].markdown("**Grupo**")
        t_cols[1].markdown("**Descrição**")
        t_cols[2].markdown("**Próximo Nº**")
        for g, desc in group_table.items():
            g_cols = st.columns([1, 2, 2])
            g_cols[0].write(f"`{g}`")
            g_cols[1].write(desc)
            key = f"seq_{g}_v{version}"
            init_val = int(st.session_state.get(key, json_state.get(g, 0)))
            g_cols[2].number_input(f"seq_{g}", min_value=0, max_value=MAX_SEQ, value=init_val, step=1, key=key, label_visibility="collapsed")

    if "last_report" in st.session_state:
        with st.container(border=True):
            st.subheader("📊 Relatório de Processamento")
            st.markdown('<div class="report-container">', unsafe_allow_html=True)
            for log in st.session_state["last_report"]:
                if log.startswith("✅"): st.markdown(f'<div class="report-item report-item-success"><div class="report-item-icon">✓</div><div>{log[2:]}</div></div>', unsafe_allow_html=True)
                elif log.startswith("✔️"): st.markdown(f'<div class="report-item report-item-success"><div class="report-item-icon">✓</div><div>{log[2:]}</div></div>', unsafe_allow_html=True)
                elif log.startswith("⚠️"): st.markdown(f'<div class="report-item report-item-warning"><div class="report-item-icon">!</div><div>{log[2:]}</div></div>', unsafe_allow_html=True)
                else: st.markdown(f'<div class="report-item report-item-info"><div class="report-item-icon">i</div><div>{log}</div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

# --- Coluna da Direita ---
with col2:
    # --- ATUALIZADO: Bloco de Upload com novo estilo ---
    with st.container(border=True):
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.subheader("1. Carregar Arquivo")
        uploaded_file = st.file_uploader(
            "Arraste e solte seu arquivo aqui ou clique para selecionar",
            type=['txt', 'xlsx'],
            label_visibility="visible" # Label é o texto principal
        )
        st.markdown("""
        <div class="formatos-suportados">
            <strong>Formatos suportados:</strong>
            <ul>
                <li>TXT: Arquivos de texto exportados do SolidWorks</li>
                <li>XLSX: Planilhas Excel</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("2. Controle de Processamento")
        b_cols = st.columns(2)
        process_clicked = b_cols[0].button("Processar Arquivo", type="primary", use_container_width=True)
        if b_cols[1].button("Resetar Campos", use_container_width=True):
            st.session_state["version"] += 1
            st.rerun()

    if "available_columns" in st.session_state:
        with st.container(border=True):
            head_cols = st.columns([1,1])
            head_cols[0].subheader("3. Selecionar Colunas")
            if head_cols[1].button("Resetar Seleção", key="reset_cols", use_container_width=True):
                for col in st.session_state.available_columns:
                    st.session_state[f"col_select_{col}"] = True
                st.session_state.select_all_cols = True
                st.rerun()
            select_all = st.checkbox("Selecionar todas", key="select_all_cols", value=st.session_state.get("select_all_cols", True))
            st.markdown("---")
            all_cols = st.session_state.available_columns
            mid_point = math.ceil(len(all_cols) / 2)
            c1, c2 = st.columns(2)
            selected_cols_list = []
            def update_select_all():
                st.session_state.select_all_cols = all(st.session_state.get(f"col_select_{c}", True) for c in all_cols)
            for i, col_name in enumerate(all_cols):
                container = c1 if i < mid_point else c2
                default_val = select_all if f"col_select_{col_name}" not in st.session_state else st.session_state.get(f"col_select_{col_name}", True)
                if container.checkbox(col_name, value=default_val, key=f"col_select_{col_name}", on_change=update_select_all):
                    selected_cols_list.append(col_name)
            st.session_state.selected_columns = [c for c in all_cols if st.session_state.get(f"col_select_{c}", True)]
            st.markdown("---")
            st.caption(f"**{len(st.session_state.selected_columns)} de {len(all_cols)} colunas selecionadas**")

# --- Seção de Dados e Download ---
if "last_df_processed" in st.session_state:
    st.markdown("---")
    st.subheader("Resultados")
    with st.container(border=True):
        st.markdown('<div style="background-color: #256D7B; padding: 20px; border-radius: 12px; color:white;">', unsafe_allow_html=True)
        st.write("<h3 style='color:white;'>📄 Dados Processados</h3>", unsafe_allow_html=True)
        dl_cols = st.columns(2)
        df_to_export = pd.read_json(io.StringIO(st.session_state["last_df_processed"]), orient='split')[st.session_state.selected_columns]
        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_data = to_excel(df_to_export)
        csv_data = df_to_export.to_csv(index=False).encode("utf-8")
        dl_cols[0].download_button("📥 Baixar Excel (.xlsx)", excel_data, f"lista_codificada_{t}.xlsx")
        dl_cols[1].download_button("📥 Baixar CSV (.csv)", csv_data, f"lista_codificada_{t}.csv")
        st.dataframe(df_to_export, use_container_width=True, height=500)
        st.markdown('</div>', unsafe_allow_html=True)

# --- Lógica de Processamento ---
if process_clicked:
    if uploaded_file is None:
        st.toast("⚠️ Por favor, carregue um arquivo.", icon="⚠️")
    else:
        sequentials = {g: int(st.session_state.get(f"seq_{g}_v{version}", 0)) for g in group_table.keys()}
        try:
            with st.spinner("Processando..."):
                df_raw, column_report, _ = load_data(uploaded_file)
                if df_raw is not None:
                    df_proc, report = process_codes(df_raw.copy(), sequentials, json_state, column_report)
                    st.session_state["last_report"] = report
                    st.session_state["last_df_processed"] = df_proc.to_json(orient='split', date_format='iso')
                    st.session_state["available_columns"] = df_proc.columns.tolist()
                    for col in df_proc.columns.tolist():
                        st.session_state[f"col_select_{col}"] = True
                    st.session_state.select_all_cols = True
            st.toast("✅ Processamento concluído!", icon="🎉")
            st.rerun()
        except Exception as e:
            st.error(f"Ocorreu um erro: {e}", icon="❌")
