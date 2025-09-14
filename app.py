import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(layout="wide", page_title="Gerador de Códigos de Itens")

# Estilo CSS com a paleta de cores final
st.markdown("""
<style>
    /* Cor de fundo principal */
    .stApp {
        background-color: #e9f5e9; /* Tom de verde claro */
    }
    /* Estilo para os cards */
    .card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    /* Estilo para os títulos com maior destaque */
    h1 {
        color: #333333; /* Cinza escuro para o título principal */
        font-weight: 700;
        border-bottom: 3px solid #333333;
        padding-bottom: 10px;
    }
    h2, h3 {
        color: #556b2f; /* Verde musgo escuro para subtítulos (palha/pastel) */
        font-weight: 700;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 8px;
        margin-top: 20px;
    }
    /* Cor do texto principal */
    body, p, label, .stMarkdown {
        color: #000000 !important; /* Texto preto */
    }
    /* Estilo para os botões */
    .stButton>button {
        background-color: #0077b6; /* Azul médio, mais escuro que o fundo */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 500;
        border-bottom: 2px solid #005f8c; /* Sombra sutil */
    }
    .stButton>button:hover {
        background-color: #005f8c; /* Tom mais escuro no hover */
    }
    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #dde8dd; /* Tom verde complementar */
        border-right: 1px solid #e0e0e0;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #556b2f;
        border-bottom: none; /* Sem borda na barra lateral */
    }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #000000 !important; /* Texto preto para contraste */
    }
    /* Cor do texto do expander (Relatório de Processamento) */
    .st-emotion-cache-115fcme summary {
        color: #556b2f !important;
        font-weight: 700;
    }
    /* Cores do relatório */
    .stAlert[data-baseweb="alert"] > div {
        border-radius: 8px;
    }

    /* FORÇAR TEMA CLARO NA TABELA (DATAFRAME) */
    [data-testid="stDataFrame"] {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] .col-header {
        background-color: #dde8dd !important;
    }
    [data-testid="stDataFrame"] .col-header-cell {
        color: #000000 !important;
        font-weight: 600;
    }
    [data-testid="stDataFrame"] .data-cell {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-color: #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---

@st.cache_data
def load_data(uploaded_file):
    """Lê o arquivo TXT com cabeçalho no final e o converte para DataFrame."""
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."

    try:
        content = uploaded_file.getvalue().decode('utf-8').splitlines()
        
        header_line_index = -1
        for i in range(len(content) - 1, -1, -1):
            if content[i].strip():
                header_line_index = i
                break

        if header_line_index == -1:
            return None, "Não foi possível encontrar o cabeçalho no arquivo."

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

        # **NOVO**: Garante que colunas essenciais existam, mesmo que vazias
        required_cols = ['Nº DA PEÇA', 'PROCESSO', 'GRUPO DE PRODUTO', 'TÍTULO']
        for col in required_cols:
            if col not in df.columns:
                df[col] = '' # Cria a coluna com valores vazios se não existir
        
        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)

        return df, "Arquivo lido com sucesso."
    except Exception as e:
        return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df):
    """Gera códigos para itens comerciais e organiza o DataFrame."""
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    df['CÓDIGO FINAL'] = df['Nº DA PEÇA']
    
    sequentials = {}
    group_pattern = re.compile(r'(\d{3})')

    for index, row in df.iterrows():
        if re.match(r'^\d{3}-\d{4}$', str(row['Nº DA PEÇA'])):
             try:
                parts = str(row['Nº DA PEÇA']).split('-')
                group, seq = parts[0], int(parts[1])
                if group not in sequentials or seq > sequentials[group]:
                    sequentials[group] = seq
             except (ValueError, IndexError):
                continue

    report_log.append(f"Sequenciais iniciais detectados: {sequentials if sequentials else 'Nenhum'}")

    for index, row in df.iterrows():
        if row['PROCESSO'] == 'Comercial':
            if re.match(r'^\d{3}-\d{4}$', str(row['Nº DA PEÇA'])):
                 continue

            group_match = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if group_match:
                group_code = group_match.group(1)
                
                current_seq = sequentials.get(group_code, 0) + 1
                sequentials[group_code] = current_seq
                
                new_code = f"{group_code}-{current_seq:04d}"
                df.loc[index, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"✔️ Item '{row['TÍTULO']}' recebeu o novo código: {new_code}")
            else:
                df.loc[index, 'CÓDIGO FINAL'] = 'ERRO: GRUPO AUSENTE'
                report_log.append(f"⚠️ Alerta: Item '{row['TÍTULO']}' é 'Comercial' mas a coluna 'GRUPO DE PRODUTO' está vazia ou inválida. Código não gerado.")

    df_fabricado = df[df['PROCESSO'] != 'Comercial']
    df_comercial = df[df['PROCESSO'] == 'Comercial']
    
    df_final = pd.concat([
        df_fabricado.sort_values(by='Nº DA PEÇA'), 
        df_comercial.sort_values(by='CÓDIGO FINAL')
    ], ignore_index=True)
    
    num_codes_generated = len([log for log in report_log if 'recebeu o novo código' in log])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    
    return df_final, report_log

@st.cache_data
def to_excel(df):
    """Converte DataFrame para um arquivo Excel em memória."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Lista de Peças')
    processed_data = output.getvalue()
    return processed_data

# --- INTERFACE DA APLICAÇÃO ---

with st.sidebar:
    st.image("https://images.unsplash.com/photo-1581092921462-63f1c1187449?q=80&w=1935&auto-format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG9tby1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", use_column_width='auto')
    st.header("1. Carregar Arquivo")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo TXT da lista de peças:",
        type=['txt']
    )
    st.info("O arquivo deve ser separado por tabulação e ter o cabeçalho na última linha.", icon="ℹ️")
    
st.title("⚙️ Gerador de Códigos para Itens Comerciais")
st.write("Esta aplicação automatiza a codificação de itens comerciais com base na sua lista de peças e na norma de codificação.")

if uploaded_file is None:
    st.info("Aguardando o upload do arquivo na barra lateral...")
else:
    try:
        with st.spinner("Lendo e processando o arquivo... Por favor, aguarde."):
            df_raw, load_message = load_data(uploaded_file)
            
            if df_raw is None:
                st.error(f"❌ {load_message}")
            else:
                df_processed, report = process_codes(df_raw.copy())
                
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    with st.expander("📄 Relatório de Processamento", expanded=True):
                        for log in report:
                            if "✔️" in log or "✅" in log:
                                st.success(log)
                            elif "⚠️" in log:
                                st.warning(log)
                            else:
                                st.info(log)
                    st.markdown('</div>', unsafe_allow_html=True)

                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.header("Lista de Peças Atualizada")
                    
                    _, col2 = st.columns([0.7, 0.3])
                    with col2:
                        sort_option = st.radio(
                            "Classificar tabela por:",
                            ("Padrão (Fabricado/Comercial)", "GRUPO DE PRODUTO", "PROCESSO"),
                            key="sort"
                        )

                    if sort_option == "Padrão (Fabricado/Comercial)":
                        df_display = df_processed
                    else:
                        df_display = df_processed.sort_values(by=sort_option).reset_index(drop=True)

                    st.dataframe(df_display, use_container_width=True)
                    
                    st.subheader("2. Exportar Resultados")
                    
                    export_cols = st.columns(2)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    with export_cols[0]:
                        st.download_button(
                            label="📥 Exportar para Excel (.xlsx)",
                            data=to_excel(df_display),
                            file_name=f'lista_codificada_{timestamp}.xlsx',
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                        )
                    with export_cols[1]:
                        st.download_button(
                            label="📥 Exportar para CSV (.csv)",
                            data=df_display.to_csv(index=False).encode('utf-8'),
                            file_name=f'lista_codificada_{timestamp}.csv',
                            mime='text/csv'
                        )
                    st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante o processamento: {e}")


