import streamlit as st
import pandas as pd
import io

st.title("Carregador de Arquivos TSV")
st.write("Faça o upload de um arquivo separado por tabulação (.tsv ou .txt) para visualizá-lo.")

uploaded_file = st.file_uploader("Escolha um arquivo", type=['tsv', 'txt'])

if uploaded_file is not None:
    try:
        string_data = io.StringIO(uploaded_file.getvalue().decode('utf-8'))
        df = pd.read_csv(string_data, sep='\t')

        st.success("✔️ Arquivo processado com sucesso!")
        st.dataframe(df)

    except Exception as e:
        st.error(f"❌ Ocorreu um erro ao processar o arquivo: {e}")
