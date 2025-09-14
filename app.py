import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(layout="wide", page_title="Gerador de Códigos de Itens")

# Estilo CSS atualizado com base no novo layout
st.markdown("""
<style>
    /* Cor de fundo principal */
    .stApp {
        background-color: #f8f9fa; /* Cinza muito claro */
    }
    /* Estilo para os cards */
    .card {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 25px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    /* Estilo para os títulos */
    h1 {
        color: #0d3b66; /* Azul corporativo escuro */
        font-weight: 700;
        padding-bottom: 10px;
    }
    h2, h3 {
        color: #0d3b66; /* Azul corporativo escuro */
        font-weight: 600;
        padding-bottom: 8px;
        margin-top: 20px;
    }
    /* Cor do texto principal */
    body, p, label, .stMarkdown {
        color: #212529 !important; /* Texto preto/cinza escuro */
    }
    /* Estilo para os botões */
    .stButton>button {
        background-color: #007bff; /* Azul primário */
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Tom mais escuro no hover */
    }
    /* Estilo para a barra lateral */
    [data-testid="stSidebar"] {
        background-color: #e9ecef; /* Cinza claro */
        border-right: 1px solid #dee2e6;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #0d3b66;
    }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #212529 !important; /* Texto escuro para contraste */
    }
    /* Cor do texto do expander (Relatório de Processamento) */
    .st-emotion-cache-115fcme summary {
        color: #0d3b66 !important;
        font-weight: 600;
    }
    /* Cores do relatório */
    .stAlert[data-baseweb="alert"] > div {
        border-radius: 8px;
    }

    /* FORÇAR TEMA CLARO NA TABELA (DATAFRAME) */
    [data-testid="stDataFrame"] {
        border: 1px solid #dee2e6;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] .col-header {
        background-color: #e9ecef !important; /* Cinza claro */
    }
    [data-testid="stDataFrame"] .col-header-cell {
        color: #212529 !important;
        font-weight: 600;
    }
    [data-testid="stDataFrame"] .data-cell {
        background-color: #ffffff !important;
        color: #212529 !important;
        border-color: #dee2e6 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---

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
    """Lê TXT (tabulado) ou XLSX e converte para DataFrame."""
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."

    try:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
            # Garante que colunas essenciais existam
            for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
                if col not in df.columns:
                    df[col] = ''
            return df, "Arquivo XLSX lido com sucesso."

        # Leitura de TXT (mesma lógica anterior, mas mais tolerante)
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

        for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
            if col not in df.columns:
                df[col] = ''

        if 'QTD.' in df.columns:
            df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)

        return df, "Arquivo TXT lido com sucesso."
    except Exception as e:
        return None, f"Erro ao ler o arquivo: {e}"

def process_codes(df, state_file):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    sequentials = load_sequentials(state_file)
    report_log.append(f"{'💾' if sequentials else 'ℹ️'} Estado sequenciais carregado: {sequentials or 'Nenhum'}")

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{4}$')

    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # Ajusta sequenciais iniciais
    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA'])
        if commercial_pattern.match(num):
            try:
                group, seq = num.split('-')
                seq = int(seq)
                if group not in sequentials or seq > sequentials[group]:
                    sequentials[group] = seq
            except:
                continue
    report_log.append(f"Sequenciais iniciais: {sequentials or 'Nenhum'}")

    # Geração de códigos
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
                sequentials[g] = sequentials.get(g, 0) + 1
                new_code = f"{g}-{sequentials[g]:04d}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                report_log.append(f"⚠️ '{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

    # Hierarquia pai-filho (corrigida)
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
    
    # Reordenar colunas
    cols = df.columns.tolist()
    if 'CÓDIGO PAI' in cols:
        cols.pop(cols.index('CÓDIGO PAI'))
        if 'CÓDIGO FINAL' in cols:
            final_code_index = cols.index('CÓDIGO FINAL')
            cols.insert(final_code_index + 1, 'CÓDIGO PAI')
            df = df[cols]


    # Ordenação lógica
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)

    # Padronizar strings
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    save_sequentials(state_file, sequentials)
    report_log.append(f"💾 Sequenciais salvos em {state_file}")
    
    num_codes_generated = len([log for log in report_log if '✔️' in log])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")

    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    processed_data = out.getvalue()
    return processed_data

# --- INTERFACE ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1581092921462-63f1c1187449?q=80&w=1935", use_column_width='auto')
    st.header("1. Carregar Arquivo")
    uploaded_file = st.file_uploader("Selecione arquivo TXT ou XLSX", type=['txt','xlsx'])
    st.info("TXT deve ser separado por tabulação com cabeçalho na última linha.", icon="ℹ️")
    st.header("2. Persistência de Códigos")
    state_file = st.text_input("Nome do arquivo de estado:", "estado_sequenciais.json")
    st.info("Salva os contadores sequenciais para evitar códigos duplicados.", icon="💾")

st.title("⚙️ Gerador de Códigos para Itens Comerciais")
st.write("Esta aplicação automatiza a codificação de itens com base na sua lista de peças.")

if not uploaded_file:
    st.info("Aguardando upload de um arquivo na barra lateral...")
else:
    try:
        with st.spinner("Processando..."):
            df_raw, msg = load_data(uploaded_file)
            if df_raw is None:
                st.error(f"❌ {msg}")
            else:
                df_proc, report = process_codes(df_raw.copy(), state_file)

                # Card de Relatório
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    with st.expander("📄 Relatório de Processamento", expanded=True):
                        for log in report:
                            if "✔️" in log or "✅" in log: st.success(log)
                            elif "⚠️" in log: st.warning(log)
                            else: st.info(log)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Card da Tabela e Exportação
                with st.container():
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    st.header("Lista de Peças Atualizada")
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
                    st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

