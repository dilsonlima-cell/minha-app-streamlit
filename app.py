import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# --- ESTILO VISUAL ---
st.markdown(
    """
    <style>
    .main {
        background-color: #fff200; /* Amarelo */
    }
    .title {
        font-size: 42px;
        font-weight: bold;
        color: #003366;
        text-align: left;
        margin-bottom: 0px;
    }
    .subtitle {
        font-size: 20px;
        color: #333333;
        text-align: left;
        margin-top: 0px;
        margin-bottom: 40px;
    }
    .upload-box {
        background-color: #fff;
        border-radius: 12px;
        padding: 25px;
        margin-top: 10px;
        margin-bottom: 20px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }
    .stDownloadButton > button, .stButton > button {
        background-color: #003366;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #0055aa;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- CABEÇALHO ---
st.markdown('<div class="title">SolidWorks BOM Processor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Processamento automático de listas de materiais exportadas do SolidWorks</div>', unsafe_allow_html=True)

# --- UPLOAD ---
with st.container():
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.subheader("📂 Upload de Arquivo BOM")
    uploaded_file = st.file_uploader("Faça upload do arquivo TXT ou XLSX exportado do SolidWorks", type=["txt", "xlsx"])
    state_file = st.text_input("Nome do arquivo de estado:", "estado_sequenciais.json")
    process_button = st.button("🚀 Processar Arquivo")
    st.markdown('</div>', unsafe_allow_html=True)

# --- FUNÇÕES (mesmas do seu script final, apenas copiadas) ---
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
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            return df, "Arquivo XLSX lido com sucesso."
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
        df = df.iloc[::-1].reset_index(drop=True)
        for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO']:
            if col not in df.columns:
                df[col] = ''
        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)
        return df, "Arquivo TXT lido com sucesso."
    except Exception as e:
        return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df, state_file):
    # (função idêntica à versão final que já corrige pai-filho, sequenciais e logs)
    # --- aqui você mantém exatamente a função que já validamos ---
    pass  # substitua pelo corpo completo da função final que já está funcionando

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- EXECUÇÃO ---
if process_button and uploaded_file:
    try:
        with st.spinner("🔄 Processando dados..."):
            df_raw, msg = load_data(uploaded_file)
            if df_raw is None:
                st.error(f"❌ {msg}")
            else:
                df_proc, report = process_codes(df_raw.copy(), state_file)

                with st.expander("📄 Relatório de Processamento", expanded=True):
                    for log in report:
                        if "✔️" in log or "✅" in log: st.success(log)
                        elif "⚠️" in log: st.warning(log)
                        else: st.info(log)

                st.subheader("📊 Lista de Peças Atualizada")
                sort_option = st.radio("Classificar por:", ("Padrão","GRUPO DE PRODUTO","PROCESSO"))
                df_show = df_proc if sort_option=="Padrão" else df_proc.sort_values(by=sort_option).reset_index(drop=True)
                st.dataframe(df_show, use_container_width=True)

                st.subheader("📥 Exportar Resultados")
                t = datetime.now().strftime("%Y%m%d_%H%M%S")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("⬇️ Baixar Excel", to_excel(df_show), f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                with col2:
                    st.download_button("⬇️ Baixar CSV", df_show.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Erro: {e}")
