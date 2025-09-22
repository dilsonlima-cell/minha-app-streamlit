import pandas as pd
import streamlit as st
from datetime import datetime
import io

# --- Função para converter DataFrame para Excel ---
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='BOM')
    output.seek(0)
    return output.getvalue()

# --- Interface do Usuário ---
st.title("Processador de BOM do SolidWorks")

# --- Seção de Upload de Arquivo ---
uploaded_file = st.file_uploader("Carregue seu arquivo de BOM", type=["txt", "xlsx"])

if uploaded_file is not None:
    # Carregar dados
    if uploaded_file.name.endswith(".txt"):
        df = pd.read_csv(uploaded_file, sep='\t')  # Ajustar separador conforme o formato
    else:
        df = pd.read_excel(uploaded_file)
    
    # Validação das colunas obrigatórias
    required_columns = ['Nº DO ITEM', 'Nº DA PEÇA', 'TÍTULO', 'QTD.', 'PROCESSO', 'GRUPO DE PRODUTO']
    if not all(col in df.columns for col in required_columns):
        st.error("Arquivo deve conter todas as colunas obrigatórias.")
    else:
        st.success("Dados carregados com sucesso!")
        
        # --- Seção de Dados e Download ---
        st.markdown("---")
        st.subheader("Resultados")
        
        # Exibir DataFrame
        with st.container(border=True):
            st.markdown('<div class="card-dark-results" style="padding: 20px; border-radius: 12px;">', unsafe_allow_html=True)
            st.write("<h3 style='color:white;'>📄 Dados Processados</h3>", unsafe_allow_html=True)
            
            # Campos de filtragem
            filters = {}
            for col in df.columns:
                filters[col] = st.text_input(f"Filtrar por {col}:", value="", key=f"filter_{col}")
            
            # Aplicar filtros
            filtered_df = df.copy()
            for col, filter_value in filters.items():
                if filter_value:
                    filtered_df = filtered_df[filtered_df[col].astype(str).str.contains(filter_value, case=False)]
            
            # Exibir DataFrame filtrado
            st.dataframe(filtered_df, use_container_width=True, height=500)

            # Botões de download
            t = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_data = to_excel(filtered_df)
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar Excel (.xlsx)", excel_data, f"lista_codificada_{t}.xlsx")
            st.download_button("📥 Baixar CSV (.csv)", csv_data, f"lista_codificada_{t}.csv")
            
            st.markdown('</div>', unsafe_allow_html=True)
