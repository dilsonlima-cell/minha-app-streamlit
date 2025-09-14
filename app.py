import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(layout="wide", page_title="Gerador de Códigos de Itens")

# Estilo CSS para um visual mais suave e atraente
st.markdown("""
<style>
    /* Cor de fundo principal */
    .stApp {
        background-color: #f0f2f6;
    }
    /* Estilo para os cards */
    .card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* Estilo para os títulos */
    h1, h2, h3 {
        color: #1e3a8a; /* Azul escuro */
    }
    /* Estilo para os botões */
    .stButton>button {
        background-color: #2563eb; /* Azul médio */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
    }
    .stButton>button:hover {
        background-color: #1d4ed8; /* Azul mais escuro */
    }
    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #e0e7ff; /* Lavanda suave */
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
                # Garante que cada linha tenha o mesmo número de colunas que o cabeçalho
                parsed_data.append(cells[:len(header)])
        
        df = pd.DataFrame(parsed_data, columns=header)
        df = df.iloc[::-1].reset_index(drop=True) # Inverte a ordem para a original
        
        # Converte a coluna 'QTD.' para numérico, tratando erros
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
    df['CÓDIGO FINAL'] = ''
    
    # Dicionário para guardar o último sequencial de cada grupo
    sequentials = {}

    # Regex para extrair o código do grupo (XXX)
    group_pattern = re.compile(r'(\d{3})')

    # Identificar o maior sequencial já existente para cada grupo (para continuar a contagem)
    for index, row in df.iterrows():
        if row['PROCESSO'] == 'Comercial' and '-' in str(row['Nº DA PEÇA']):
             try:
                parts = str(row['Nº DA PEÇA']).split('-')
                group = parts[0]
                seq = int(parts[1])
                if group in sequentials:
                    if seq > sequentials[group]:
                        sequentials[group] = seq
                else:
                    sequentials[group] = seq
             except (ValueError, IndexError):
                continue # Ignora códigos comerciais mal formatados

    report_log.append(f"Sequenciais iniciais detectados: {sequentials if sequentials else 'Nenhum'}")

    # Processamento para gerar novos códigos
    for index, row in df.iterrows():
        is_manufactured = bool(re.match(r'^\d{2}-\d{4}-\d{4}-\d{2}$', str(row['Nº DA PEÇA'])))
        
        if is_manufactured or row['PROCESSO'] != 'Comercial':
            df.loc[index, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
        else: # É item comercial e precisa de um código novo ou já tem
            
            # Se já tem um código comercial válido, mantém
            if re.match(r'^\d{3}-\d{4}$', str(row['Nº DA PEÇA'])):
                 df.loc[index, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
                 continue

            group_match = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if group_match:
                group_code = group_match.group(1)
                
                # Incrementa o sequencial do grupo
                current_seq = sequentials.get(group_code, 0) + 1
                sequentials[group_code] = current_seq
                
                new_code = f"{group_code}-{current_seq:04d}"
                df.loc[index, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"✔️ Item '{row['TÍTULO']}' do grupo '{row['GRUPO DE PRODUTO']}' recebeu o novo código: {new_code}")
            else:
                df.loc[index, 'CÓDIGO FINAL'] = 'ERRO: GRUPO NÃO IDENTIFICADO'
                report_log.append(f"⚠️ Alerta: Não foi possível identificar o grupo para o item '{row['TÍTULO']}'.")

    # Separar, ordenar e juntar
    df_fabricado = df[df['PROCESSO'] != 'Comercial'].sort_values(by='CÓDIGO FINAL')
    df_comercial = df[df['PROCESSO'] == 'Comercial'].sort_values(by='CÓDIGO FINAL')
    
    df_final = pd.concat([df_fabricado, df_comercial], ignore_index=True)
    
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

# Barra Lateral
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1581092921462-63f1c1187449?q=80&w=1935&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", use_column_width=True)
    st.header("1. Carregar Arquivo")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo TXT da lista de peças do SolidWorks:",
        type=['txt']
    )
    st.info("O arquivo deve ser separado por tabulação e ter o cabeçalho na última linha.", icon="ℹ️")
    
# Título Principal
st.title("⚙️ Gerador de Códigos para Itens Comerciais")
st.write("Esta aplicação automatiza a codificação de itens comerciais com base na sua lista de peças e na norma de codificação.")

# Corpo Principal
if uploaded_file is None:
    st.info("Aguardando o upload do arquivo na barra lateral...")
else:
    with st.spinner("Lendo e processando o arquivo... Por favor, aguarde."):
        df_raw, load_message = load_data(uploaded_file)
        
        if df_raw is None:
            st.error(f"❌ {load_message}")
        else:
            df_processed, report = process_codes(df_raw.copy())
            
            # Card para Relatório
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                with st.expander("📄 Relatório de Processamento", expanded=True):
                    for log in report:
                        if "✔️" in log or "✅" in log:
                            st.write(log)
                        elif "⚠️" in log:
                            st.warning(log)
                        else:
                            st.info(log)
                st.markdown('</div>', unsafe_allow_html=True)

            # Card para a Tabela e Opções de Exportação
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.header("Lista de Peças Atualizada")
                
                col1, col2 = st.columns([0.7, 0.3])
                with col2:
                    sort_option = st.radio(
                        "Classificar tabela por:",
                        ("Padrão (Código Final)", "GRUPO DE PRODUTO", "PROCESSO"),
                        key="sort"
                    )

                # Aplica a classificação
                if sort_option == "Padrão (Código Final)":
                    df_display = df_processed
                else:
                    df_display = df_processed.sort_values(by=sort_option).reset_index(drop=True)

                st.dataframe(df_display, use_container_width=True)
                
                st.subheader("2. Exportar Resultados")
                
                export_cols = st.columns(2)
                
                # Gerar nome do arquivo com data e hora
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

