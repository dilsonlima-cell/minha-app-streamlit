import streamlit as st
import pandas as pd
import io

st.title("Analisador de Dados de Cidades")
st.write("Faça o upload de um arquivo TSV para filtrar e visualizar os dados.")

uploaded_file = st.file_uploader("Escolha um arquivo", type=['tsv', 'txt'])

if uploaded_file is not None:
    try:
        string_data = io.StringIO(uploaded_file.getvalue().decode('utf-8'))
        df = pd.read_csv(string_data, sep='\t')
        
        st.success("✔️ Arquivo processado com sucesso!")
        
        # --- NOVIDADE AQUI ---
        st.header("Filtro Interativo")
        
        # 1. Pega a lista de cidades únicas e adiciona a opção "Todos"
        lista_cidades = list(df['Cidade'].unique())
        lista_cidades.insert(0, "Todos")
        
        # 2. Cria a caixa de seleção para o usuário escolher
        cidade_selecionada = st.selectbox("Selecione uma cidade para filtrar:", lista_cidades)
        
        # 3. Filtra o DataFrame com base na seleção
        if cidade_selecionada == "Todos":
            df_filtrado = df
        else:
            df_filtrado = df[df['Cidade'] == cidade_selecionada]
            
        # 4. Exibe a tabela com os dados filtrados
        st.write(f"Exibindo dados para: **{cidade_selecionada}**")
        st.dataframe(df_filtrado)
        # --- FIM DA NOVIDADE ---

    except Exception as e:
        st.error(f"❌ Ocorreu um erro ao processar o arquivo: {e}")
