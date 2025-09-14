import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# --- ESTILO VISUAL (CSS CUSTOMIZADO) ---
st.markdown(
    """
    <style>
    /* Fundo geral */
    .main {
        background-color: #fff200; /* Amarelo */
    }

    /* Cabeçalho */
    .title {
        font-size: 42px;
        font-weight: bold;
        color: #003366; /* Azul escuro */
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

    /* Caixa principal (upload) */
    .upload-box {
        background-color: #fff;
        border-radius: 12px;
        padding: 25px;
        margin-top: 10px;
        margin-bottom: 20px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
    }

    /* Botões */
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

# --- UPLOAD DE ARQUIVO ---
with st.container():
    st.markdown('<div class="upload-box">', unsafe_allow_html=True)
    st.subheader("📂 Upload de Arquivo BOM")
    uploaded_file = st.file_uploader("Faça upload do arquivo TXT ou XLSX exportado do SolidWorks", type=["txt", "xlsx"])
    process_button = st.button("🚀 Processar Arquivo")
    st.markdown('</div>', unsafe_allow_html=True)

# --- FUNÇÕES DE PROCESSAMENTO (mesmas que já estavam implementadas) ---
def process_data(uploaded_file):
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."
    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file, sep="\t")
        return df, "Arquivo carregado com sucesso."
    except Exception as e:
        return None, f"Erro: {e}"

# --- EXECUÇÃO ---
if process_button and uploaded_file:
    with st.spinner("🔄 Processando dados..."):
        df, msg = process_data(uploaded_file)
        if df is None:
            st.error(msg)
        else:
            st.success(msg)

            # Exibir tabela
            st.subheader("📊 Lista Processada")
            st.dataframe(df, use_container_width=True)

            # Exportação
            st.subheader("📥 Exportar Resultados")
            t = datetime.now().strftime("%Y%m%d_%H%M%S")

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Baixar Excel",
                    df.to_excel(io.BytesIO(), index=False, engine="xlsxwriter"),
                    f"lista_codificada_{t}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                st.download_button(
                    "⬇️ Baixar CSV",
                    df.to_csv(index=False).encode("utf-8"),
                    f"lista_codificada_{t}.csv",
                    mime="text/csv"
                )
