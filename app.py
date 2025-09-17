import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- PALETA DE CORES (ATUALIZADA) ---
COLOR_PALETTE = {
    "dark_green": "#255000",
    "medium_green": "#588100",
    "lime_green": "#8db600",
    "light_yellow_green": "#c6da52",
    "pale_yellow": "#ffff8b",
    "dark_gray_text": "#434D36",
    "white": "#FFFFFF",
    "off_white_bg": "#F8F9FA",
    "light_gray_border": "#dee2e6",
    "button_hover": "#255000"
}

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# --- FUNÇÕES JSON ---
STATE_FILE = "estado_sequenciais.json"

def load_sequentials(file_path=STATE_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sequentials(data, file_path=STATE_FILE):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# --- ESTILO CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_PALETTE["off_white_bg"]}; color: {COLOR_PALETTE["dark_gray_text"]}; }}
    .header-bar {{ background-color: {COLOR_PALETTE["dark_green"]}; padding: 10px 50px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .header-bar h1, .header-bar .stMarkdown p {{ color: {COLOR_PALETTE["white"]}; margin: 0; }}
    .header-nav {{ display: flex; gap: 20px; }}
    .header-nav .stMarkdown p {{ color: {COLOR_PALETTE["light_yellow_green"]}; cursor: pointer; transition: color 0.2s; }}
    .header-nav .stMarkdown p:hover {{ color: {COLOR_PALETTE["white"]}; }}
    .start-processing-section {{ background-color: {COLOR_PALETTE["lime_green"]}; padding: 40px; text-align: center; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .card {{ background-color: {COLOR_PALETTE["white"]}; border: 1px solid {COLOR_PALETTE["light_gray_border"]}; border-radius: 10px; padding: 25px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    h1, h2, h3 {{ color: {COLOR_PALETTE["dark_green"]}; font-weight: 600; }}
    .stButton>button {{ background-color: {COLOR_PALETTE["medium_green"]}; color: {COLOR_PALETTE["white"]}; border-radius: 8px; border: none; padding: 10px 24px; font-weight: 500; transition: background-color 0.2s; }}
    .stButton>button:hover {{ background-color: {COLOR_PALETTE["button_hover"]}; color: {COLOR_PALETTE["white"]}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_PALETTE["light_yellow_green"]}; border-right: 1px solid #D9E1CC; }}
</style>
""", unsafe_allow_html=True)

# --- FUNÇÃO AUXILIAR PARA CARD ---
@contextmanager
def card_container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
                if col not in df.columns:
                    df[col] = ''
            return df, "Arquivo XLSX lido com sucesso."

        content = uploaded_file.getvalue().decode('utf-8').splitlines()
        header = [h.strip() for h in content[-1].split('\t')]
        data_lines = content[:-1]

        parsed_data = []
        for line in data_lines:
            if line.strip():
                cells = [cell.strip() for cell in line.split('\t')]
                while len(cells) < len(header):
                    cells.append('')
                parsed_data.append(cells[:len(header)])
        
        df = pd.DataFrame(parsed_data, columns=header)
        df = df.iloc[::-1].reset_index(drop=True)

        for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
            if col not in df.columns:
                df[col] = ''

        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)

        return df, "Arquivo TXT lido com sucesso."
    except Exception as e:
        return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df, sequentials, json_state):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    report_log.append(f"ℹ️ Sequenciais carregados manualmente: {sequentials}")
    report_log.append(f"📂 Sequenciais do arquivo JSON: {json_state}")

    # Priorizar o maior valor (digitado ou do JSON)
    for g in sequentials:
        sequentials[g] = max(sequentials[g], json_state.get(g, 0))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{6}$')  # agora 6 dígitos

    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # Atualizar sequenciais com base nos códigos já existentes
    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA'])
        if commercial_pattern.match(num):
            try:
                group, seq = num.split('-')
                seq = int(seq)
                sequentials[group] = max(sequentials.get(group, 0), seq)
            except:
                continue

    report_log.append(f"Sequenciais ajustados após leitura da BOM: {sequentials}")

    # Geração dos códigos (unicidade garantida, 6 dígitos fixos)
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
                next_code = sequentials.get(g, 0) + 1
                while f"{g}-{next_code:06d}" in df['CÓDIGO FINAL'].values:
                    next_code += 1
                sequentials[g] = next_code
                new_code = f"{g}-{sequentials[g]:06d}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                report_log.append(f"⚠️ '{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

    # Hierarquia pai-filho
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

    # Ordenação
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)

    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    save_sequentials(sequentials)  # salvar atualização
    report_log.append("💾 Sequenciais atualizados no estado_sequenciais.json")

    num_codes_generated = len([log for log in report_log if '✔️' in log])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")

    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- INTERFACE ---

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

with st.sidebar:
    st.header("1. Carregar Arquivo")
    uploaded_file = st.file_uploader("Selecione arquivo TXT ou XLSX", type=['txt','xlsx'])

# --- TABELA DE GRUPOS (MANUAL) ---
st.header("Tabela de Grupos – Próximo Código")

group_table = {
    "100": "Mecânico",
    "200": "Elétrico",
    "300": "Hidráulico Água",
    "400": "Hidráulico Óleo",
    "500": "Pneumático",
    "600": "Tecnologia",
    "700": "Infraestrutura",
    "800": "Insumos",
    "900": "Segurança",
    "950": "Serviço"
}

sequentials = {}
cols = st.columns([1,2,2])
cols[0].markdown("**Grupo**")
cols[1].markdown("**Descrição**")
cols[2].markdown("**Próximo Código**")

for g, desc in group_table.items():
    cols = st.columns([1,2,2])
    cols[0].write(g)
    cols[1].write(desc)
    sequentials[g] = cols[2].number_input(
        f"Próximo código para grupo {g}",
        min_value=0, value=0, step=1,
        key=f"seq_{g}"
    )

# --- PROCESSAMENTO ---
st.markdown('<div class="start-processing-section">', unsafe_allow_html=True)
st.header("Começar Processamento")
st.write("Faça upload do arquivo TXT/XLSX exportado do SolidWorks e configure os grupos acima.")
st.markdown('</div>', unsafe_allow_html=True)

if not uploaded_file:
    st.info("Aguardando upload de um arquivo para começar...", icon="👆")
else:
    try:
        with st.spinner("Processando..."):
            df_raw, msg = load_data(uploaded_file)
            if df_raw is None:
                st.error(f"❌ {msg}")
            else:
                json_state = load_sequentials()
                df_proc, report = process_codes(df_raw.copy(), sequentials, json_state)

                # 🔄 Limpa os campos após o processamento
                for g in group_table.keys():
                    st.session_state[f"seq_{g}"] = 0

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
                        sort_option = st.radio("Classificar por:", ("Padrão","GRUPO DE PRODUTO","PROCESSO"), horizontal=True)
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
