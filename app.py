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

# --- Estilo (Inspirado no novo layout React) ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# Função para converter imagens para base64
def get_image_as_base64(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except IOError:
        return None # Retorna None se a imagem não for encontrada

# --- ATUALIZADO: Carregando imagens ---
logo_base64 = get_image_as_base64("logo.png") # Opcional, para o placeholder
hero_image_base64 = get_image_as_base64("hero-solidworks.jpg")

hero_style = ""
if hero_image_base64:
    hero_style = f"""
    background-image: linear-gradient(rgba(40, 40, 40, 0.8), rgba(40, 40, 40, 0.7)), url(data:image/jpeg;base64,{hero_image_base64});
    background-size: cover;
    background-position: center;
    """
else:
    # Estilo fallback caso a imagem não exista
    hero_style = "background: linear-gradient(45deg, #256D7B, #7E8C54);"


# --- ATUALIZADO: CSS Moderno ---
st.markdown(f"""
<style>
    /* --- GERAL --- */
    .stApp {{
        background-color: #f0f2f6; /* Fundo mais claro */
        color: #333;
    }}
    h1, h2, h3 {{
        color: #1a202c !important;
    }}
    .stButton > button {{
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        width: 100%;
        transition: all 0.2s ease-in-out;
    }}
    .stButton > button:hover {{
        filter: brightness(1.1);
    }}
    
    /* --- CARD STYLES --- */
    .card {{
        background-color: #FFFFFF;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
        margin-bottom: 20px; /* Adiciona espaçamento entre os cards */
    }}
    
    /* --- HEADER --- */
    .hero-header {{
        {hero_style}
        padding: 4rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
    }}
    .hero-header h1 {{
        font-size: 2.8rem;
        font-weight: 700;
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.4);
    }}
    .hero-header p {{
        font-size: 1.2rem;
        color: rgba(255, 255, 255, 0.9) !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        max-width: 600px;
    }}
    
    /* --- UPLOADER DE ARQUIVO --- */
    [data-testid="stFileUploader"] {{
        border: 2px dashed #cbd5e0;
        border-radius: 8px;
        padding: 20px;
    }}
    
    /* --- RELATÓRIO --- */
    .report-item {{
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 5px;
        border-left: 5px solid;
    }}
    .report-item-success {{ background-color: #f0fff4; border-color: #38a169; }}
    .report-item-info {{ background-color: #ebf8ff; border-color: #3182ce; }}
    .report-item-warning {{ background-color: #fffaf0; border-color: #dd6b20; }}
    .report-item-error {{ background-color: #fff5f5; border-color: #c53030; }}
</style>
""", unsafe_allow_html=True)

# --- JSON helpers ---
def load_sequentials(file_path=STATE_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except json.JSONDecodeError: return {}
    return {}

def save_sequentials(data, file_path=STATE_FILE):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- load file helper ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, [], "Nenhum arquivo carregado."
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
    except Exception as e:
        return None, [], f"Erro ao ler o arquivo: {e}"

# --- process logic ---
def process_codes(df, sequentials, json_state, column_report):
    if df is None or df.empty: return pd.DataFrame(), [], "DataFrame vazio."
    report_log = list(column_report)
    for g in sequentials.keys():
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')
    
    df['PROCESSO'] = df['PROCESSO'].astype(str).str.strip().str.upper()
    empty_process = df['PROCESSO'].isin(['', 'NAN', None]) | pd.isna(df['PROCESSO'])
    
    count_filled = 0
    for i in df[empty_process].index:
        is_manufactured = manufactured_pattern.match(str(df.loc[i, 'Nº DA PEÇA']))
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if is_manufactured else 'COMERCIAL'
        count_filled += 1
    if count_filled > 0: report_log.append(f"✔️ 'PROCESSO' preenchido para **{count_filled}** itens.")
    
    df['CÓDIGO FINAL'] = 'NULO'
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA',''))
        if m := commercial_pattern.match(num):
            try:
                group, seq_str = num.split('-')
                sequentials[group] = max(sequentials.get(group, 0), int(seq_str))
            except: continue

    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue
        num = str(row.get('Nº DA PEÇA',''))
        if (m_direct := commercial_pattern.match(num)) and len(m_direct.group(1)) == 6:
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
            report_log.append(f"✔️ '{row.get('TÍTULO','')}' recebeu o código: **{new_code}**")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO','')}' COMERCIAL sem grupo -> NULO")

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
    report_log.append("💾 Sequenciais atualizados no arquivo.")
    num_codes = len([l for l in report_log if l.startswith("✔️ '")])
    report_log.insert(0, f"✅ Processamento concluído. **{num_codes}** novos códigos gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- ATUALIZADO: Interface --- #

# --- NOVO: Cabeçalho Hero ---
st.markdown("""
<div class="hero-header">
    <h1>SolidWorks BOM Processor</h1>
    <p>Processamento automático de listas de materiais exportadas do SolidWorks.</p>
</div>
""", unsafe_allow_html=True)

# --- NOVO: Layout de duas colunas para controles ---
col1, col2 = st.columns([5, 7])

# --- Coluna da Esquerda (Configurações e Relatório) ---
with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚙️ Tabela de Grupos – Próximo Código")
    
    group_table = {
        "100":"Mecânico", "200":"Elétrico", "300":"Hidráulico Água", "400":"Hidráulico Óleo",
        "500":"Pneumático", "600":"Tecnologia", "700":"Infraestrutura", "800":"Insumos",
        "900":"Segurança", "950":"Serviço"
    }
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
    
    st.markdown('</div>', unsafe_allow_html=True)

    if "last_report" in st.session_state:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📊 Relatório de Processamento")
        for log in st.session_state["last_report"]:
            if   log.startswith("✔️") or log.startswith("✅"): st.markdown(f'<div class="report-item report-item-success">{log}</div>', unsafe_allow_html=True)
            elif log.startswith("⚠️"): st.markdown(f'<div class="report-item report-item-warning">{log}</div>', unsafe_allow_html=True)
            elif log.startswith("❌"): st.markdown(f'<div class="report-item report-item-error">{log}</div>', unsafe_allow_html=True)
            else: st.markdown(f'<div class="report-item report-item-info">{log}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- Coluna da Direita (Ações) ---
with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📤 1. Carregar Arquivo")
    uploaded_file = st.file_uploader(
        "Arraste ou selecione o arquivo TXT ou XLSX",
        type=['txt', 'xlsx'],
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("⚡ 2. Controle de Processamento")
    st.write("Configure os grupos à esquerda e clique para iniciar.")
    
    b_cols = st.columns(2)
    process_clicked = b_cols[0].button("Processar Arquivo", type="primary", use_container_width=True)
    if b_cols[1].button("Resetar Campos", use_container_width=True):
        st.session_state["version"] += 1
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if "available_columns" in st.session_state:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📋 3. Selecionar Colunas para Exportar")
        st.session_state.selected_columns = st.multiselect(
            "Escolha as colunas para o arquivo final:",
            options=st.session_state.available_columns,
            default=st.session_state.get("selected_columns", st.session_state.available_columns),
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📥 4. Exportação")
        df_to_export = pd.read_json(io.StringIO(st.session_state["last_df_processed"]), orient='split')[st.session_state.selected_columns]
        
        dl_cols = st.columns(2)
        t = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_data = to_excel(df_to_export)
        csv_data = df_to_export.to_csv(index=False).encode("utf-8")
        dl_cols[0].download_button("Baixar Excel (.xlsx)", excel_data, f"lista_codificada_{t}.xlsx", use_container_width=True)
        dl_cols[1].download_button("Baixar CSV (.csv)", csv_data, f"lista_codificada_{t}.csv", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- NOVO: Seção da Tabela de Dados (Largura Total) ---
if "last_df_processed" in st.session_state:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📄 Dados Processados")
    df_display = pd.read_json(io.StringIO(st.session_state["last_df_processed"]), orient='split')
    st.dataframe(df_display[st.session_state.get("selected_columns", df_display.columns.tolist())], use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# --- Lógica de Processamento ---
if process_clicked:
    if uploaded_file is None:
        st.toast("⚠️ Por favor, carregue um arquivo antes de processar.", icon="⚠️")
    else:
        sequentials = {g: int(st.session_state.get(f"seq_{g}_v{version}", 0)) for g in group_table.keys()}
        try:
            with st.spinner("Processando... Por favor, aguarde."):
                df_raw, column_report, _ = load_data(uploaded_file)
                if df_raw is not None:
                    df_proc, report = process_codes(df_raw.copy(), sequentials, json_state, column_report)
                    st.session_state["last_report"] = report
                    st.session_state["last_df_processed"] = df_proc.to_json(orient='split', date_format='iso')
                    st.session_state["available_columns"] = df_proc.columns.tolist()
            st.toast("✅ Processamento concluído com sucesso!", icon="🎉")
            st.rerun()
        except Exception as e:
            st.toast(f"❌ Erro: {e}", icon="❌")
