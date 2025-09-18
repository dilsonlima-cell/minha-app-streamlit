import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# ESTILO VISUAL PERSONALIZADO
st.markdown("""
<style>
    .main-container { display: flex; gap: 30px; }
    .left-panel, .right-panel {
        padding: 20px;
        border-radius: 10px;
    }
    .left-panel { background-color: #f4f7f9; width: 30%; }
    .right-panel { background-color: #ffffff; width: 70%; }
    .logo-title { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .logo-title img { height: 60px; }
    .logo-title h1 { font-size: 24px; color: #2c3e50; margin: 0; }
    .section { margin-bottom: 30px; }
    .section h3 { color: #2c3e50; margin-bottom: 10px; }
    .stButton>button {
        background-color: #2c3e50;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1a252f;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# LOGOTIPO E TÍTULO
st.markdown('<div class="logo-title">', unsafe_allow_html=True)
col_logo, col_title = st.columns([1, 5])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png")
    else:
        st.warning("⚠️ Logotipo não encontrado. Certifique-se de que 'logo.png' está na pasta do app.")
with col_title:
    st.markdown("<h1>SOLIDWORKS BOM PROCESSOR</h1>", unsafe_allow_html=True)
    st.caption("PROCESSAMENTO AUTOMÁTICO DE LISTAS DE MATERIAIS EXPORTADAS DO SOLIDWORKS")
st.markdown('</div>', unsafe_allow_html=True)
# ARQUIVO DE ESTADO
ESTADO_FILE = "estado_sequenciais.json"

def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                return {str(k): int(v) for k, v in json.load(f).items()}
        except:
            return {}
    return {}

def salvar_estado(sequentials):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(sequentials, f, ensure_ascii=False, indent=4)

def construir_codigos_existentes(estado):
    existentes = set()
    for grupo, ultimo in estado.items():
        for seq in range(1, ultimo + 1):
            existentes.add(f"{grupo}-{str(seq).zfill(6)}")
    return existentes

def verificar_duplicatas(df, estado):
    existentes = construir_codigos_existentes(estado)
    padrao = re.compile(r'^\d{3}-\d{6}$')
    return sorted(set(c for c in df['Nº DA PEÇA'].astype(str) if padrao.match(c) and c in existentes))

@st.cache_data
def load_data(uploaded_file):
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
    else:
        content = uploaded_file.getvalue().decode('utf-8').splitlines()
        header = content[-1].split('\t')
        data = [line.split('\t') for line in content[:-1]]
        df = pd.DataFrame(data, columns=header)
        df = df.iloc[::-1].reset_index(drop=True)
    for col in ['Nº DA PEÇA','PROCESSO','GRUPO DE PRODUTO','TÍTULO', 'Nº DO ITEM']:
        if col not in df.columns:
            df[col] = ''
    return df, "Arquivo carregado com sucesso."

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()
def process_codes(df, sequentials):
    estado = carregar_estado()
    for g in sequentials:
        sequentials[g] = max(sequentials[g], estado.get(g, 0))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{6}$')

    df['PROCESSO'] = df['Nº DA PEÇA'].apply(lambda x: 'FABRICADO' if manufactured_pattern.match(str(x)) else 'COMERCIAL')
    df['CÓDIGO FINAL'] = 'NULO'

    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA']).strip()
        if commercial_pattern.match(num):
            group, seq = num.split('-')
            seq = int(seq)
            if group not in sequentials or seq > sequentials[group]:
                sequentials[group] = seq

    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
        elif commercial_pattern.match(str(row['Nº DA PEÇA'])):
            df.loc[i, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
        else:
            m = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if m:
                g = m.group(1)
                sequentials[g] = sequentials.get(g, 0) + 1
                df.loc[i, 'CÓDIGO FINAL'] = f"{g}-{str(sequentials[g]).zfill(6)}"

    salvar_estado(sequentials)

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
    df['TIPO'] = df.apply(lambda row: 1 if row['PROCESSO']=='FABRICADO' else 2 if row['CÓDIGO FINAL']!='NULO' else 3, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()
    return df
# INTERFACE PRINCIPAL
estado_atual = carregar_estado()
total_existentes = sum(estado_atual.values())

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# PAINEL ESQUERDO
st.markdown('<div class="left-panel">', unsafe_allow_html=True)
st.subheader("📊 Tabela de Grupos – Próximo Código (6 dígitos)")
group_table = {
    "100": "Mecânico", "200": "Elétrico", "300": "Hidráulico Água",
    "400": "Hidráulico Óleo", "500": "Pneumático", "600": "Tecnologia",
    "700": "Infraestrutura", "800": "Insumos", "900": "Segurança", "950": "Serviço"
}
sequentials = {}
for g, desc in group_table.items():
    sequentials[g] = st.number_input(f"{g} – {desc}", min_value=0, value=estado_atual.get(g, 0), step=1)

st.subheader("📁 Carregar Arquivo")
uploaded_file = st.file_uploader("Selecione um arquivo TXT ou XLSX", type=['txt','xlsx'])
st.markdown(f"**Histórico:** {total_existentes} códigos já registrados.")
st.markdown('</div>', unsafe_allow_html=True)

# PAINEL DIREITO
st.markdown('<div class="right-panel">', unsafe_allow_html=True)

if uploaded_file:
    df_raw, msg = load_data(uploaded_file)
    if df_raw is None:
        st.error(f"❌ {msg}")
    else:
        repetidos = verificar_duplicatas(df_raw, carregar_estado())
        if repetidos:
            st.error("🚫 O arquivo contém códigos comerciais já existentes no histórico.")
            st.write(", ".join(repetidos))
        else:
            if st.button("🚀 Processar Lista"):
                df_proc = process_codes(df_raw.copy(), sequentials)

                st.subheader("📄 Relatório de Processamento")
                st.success("✅ Processamento concluído com sucesso.")

                st.subheader("📊 Dados Processados")
                filtro = st.selectbox("Filtrar por:", ["Todos", "Grupo", "Processo", "Código"])
                df_show = df_proc.copy()

                if filtro == "Grupo":
                    grupos = sorted(df_show['GRUPO DE PRODUTO'].unique())
                    grupo_sel = st.selectbox("Selecione o grupo:", grupos)
                    df_show = df_show[df_show['GRUPO DE PRODUTO'] == grupo_sel]
                elif filtro == "Processo":
                    proc_sel = st.selectbox("Selecione o processo:", ["FABRICADO", "COMERCIAL"])
                    df_show = df_show[df_show['PROCESSO'] == proc_sel]
                elif filtro == "Código":
                    cod_sel = st.text_input("Digite parte do código:")
                    df_show = df_show[df_show['CÓDIGO FINAL'].str.contains(cod_sel.upper())]

                st.dataframe(df_show, use_container_width=True)

                st.subheader("📤 Exportar Resultados")
                t = datetime.now().strftime("%Y%m%d_%H%M%S")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📥 Excel", to_excel(df_show), f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                with col2:
                    st.download_button("📥 CSV", df_show.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", mime="text/csv")

                # Limpa campos após processamento
                for g in group_table.keys():
                    st.session_state[f"seq_{g}"] = 0

st.markdown('</div>', unsafe_allow_html=True)  # fecha right-panel
st.markdown('</div>', unsafe_allow_html=True)  # fecha main-container
