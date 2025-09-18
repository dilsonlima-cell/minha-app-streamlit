import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
<style>
    .main-container {
        display: flex;
        flex-direction: row;
        gap: 30px;
    }
    .left-column {
        flex: 1;
        padding: 20px;
        background-color: #f4f7f9;
        border-radius: 10px;
    }
    .right-column {
        flex: 2;
        padding: 20px;
        background-color: #ffffff;
        border-radius: 10px;
    }
    .section {
        margin-bottom: 30px;
    }
    .section h3 {
        color: #2c3e50;
        margin-bottom: 10px;
    }
    .logo-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 20px;
    }
    .logo-container img {
        height: 60px;
    }
    .logo-container h1 {
        font-size: 24px;
        color: #2c3e50;
        margin: 0;
    }
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

# --- LOGOTIPO E TÍTULO ---
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("logo.png")
with col_title:
    st.markdown("<h1>SolidWorks BOM Processor</h1>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
# --- PERSISTÊNCIA DE ESTADO ---
ESTADO_FILE = "estado_sequenciais.json"

def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {str(k): int(v) for k, v in data.items()}
        except Exception:
            return {}
    return {}

def salvar_estado(sequentials):
    safe = {str(k): int(v) for k, v in sequentials.items() if isinstance(v, (int, float))}
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(safe, f, ensure_ascii=False, indent=4)

def construir_codigos_existentes(estado):
    existentes = set()
    for grupo, ultimo in estado.items():
        try:
            ultimo = int(ultimo)
        except:
            continue
        for seq in range(1, ultimo + 1):
            existentes.add(f"{grupo}-{str(seq).zfill(6)}")
    return existentes

def verificar_duplicatas(df, estado):
    existentes = construir_codigos_existentes(estado)
    repetidos = []
    padrao = re.compile(r'^\d{3}-\d{6}$')
    for codigo in df['Nº DA PEÇA'].astype(str):
        if padrao.match(codigo) and codigo in existentes:
            repetidos.append(codigo)
    return sorted(set(repetidos))

# --- LEITURA DE ARQUIVOS ---
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

# --- EXPORTAÇÃO PARA EXCEL ---
@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- CONTEXT MANAGER PARA SEÇÃO VISUAL ---
@contextmanager
def card_container():
    st.markdown('<div style="border:1px solid #ccc; padding:20px; border-radius:10px; margin-bottom:20px;">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)
def process_codes(df, sequentials):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    estado = carregar_estado()

    # Mescla manual vs persistido: usar o maior
    for g in sequentials:
        sequentials[g] = max(int(sequentials[g]), int(estado.get(g, 0)))

    report_log.append(f"ℹ️ Sequenciais carregados manualmente (ajustados pelo histórico): {sequentials}")

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{6}$')  # 3 + 6 dígitos

    # Preencher processo
    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # Ajusta sequenciais com base nos códigos já existentes no arquivo (XXX-YYYYYY)
    for _, row in df.iterrows():
        num = str(row['Nº DA PEÇA']).strip()
        if commercial_pattern.match(num):
            try:
                group, seq = num.split('-')
                seq = int(seq)
                if group not in sequentials or seq > int(sequentials[group]):
                    sequentials[group] = seq
            except:
                continue
    report_log.append(f"Sequenciais ajustados com base no arquivo: {sequentials}")

    # Geração dos códigos
    novos_codigos = 0
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row['Nº DA PEÇA']
            continue
        if row['PROCESSO'] == 'COMERCIAL':
            num = str(row['Nº DA PEÇA']).strip()
            if commercial_pattern.match(num):
                df.loc[i, 'CÓDIGO FINAL'] = num
                continue
            m = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if m:
                g = m.group(1)
                sequentials[g] = int(sequentials.get(g, 0)) + 1
                new_code = f"{g}-{str(sequentials[g]).zfill(6)}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
                novos_codigos += 1
            else:
                report_log.append(f"⚠️ '{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

    # Salva estado atualizado com os maiores sequenciais por grupo
    salvar_estado(sequentials)

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

    report_log.insert(0, f"✅ Processamento concluído. {novos_codigos} novos códigos comerciais foram gerados.")
    return df, report_log
# --- INTERFACE PRINCIPAL ---
estado_atual = carregar_estado()
total_existentes = sum(int(v) for v in estado_atual.values()) if estado_atual else 0

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# --- COLUNA ESQUERDA: CONFIGURAÇÕES ---
st.markdown('<div class="left-column">', unsafe_allow_html=True)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("📊 Tabela de Grupos – Próximo Código (6 dígitos)")
group_table = {
    "100": "Mecânico", "200": "Elétrico", "300": "Hidráulico Água",
    "400": "Hidráulico Óleo", "500": "Pneumático", "600": "Tecnologia",
    "700": "Infraestrutura", "800": "Insumos", "900": "Segurança", "950": "Serviço"
}
sequentials = {}
for g, desc in group_table.items():
    sequentials[g] = st.number_input(
        f"{g} – {desc}", min_value=0,
        value=int(estado_atual.get(g, 0)), step=1,
        key=f"seq_{g}"
    )
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("📁 Carregar Arquivo")
uploaded_file = st.file_uploader("Selecione um arquivo TXT ou XLSX", type=['txt','xlsx'])
st.markdown(f"**Histórico:** {total_existentes} códigos já registrados.")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section">', unsafe_allow_html=True)
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
                df_proc, report = process_codes(df_raw.copy(), sequentials)

                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)  # fecha coluna esquerda

                # --- COLUNA DIREITA: RESULTADOS ---
                st.markdown('<div class="right-column">', unsafe_allow_html=True)

                st.markdown('<div class="section">', unsafe_allow_html=True)
                st.subheader("📄 Relatório de Processamento")
                for log in report:
                    if "✔️" in log or "✅" in log: st.success(log)
                    elif "⚠️" in log: st.warning(log)
                    else: st.info(log)
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="section">', unsafe_allow_html=True)
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
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="section">', unsafe_allow_html=True)
                st.subheader("📤 Exportar Resultados")
                t = datetime.now().strftime("%Y%m%d_%H%M%S")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📥 Excel", to_excel(df_show), f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                with col2:
                    st.download_button("📥 CSV", df_show.to_csv(index=False).encode("utf-8"), f"lista_codificada_{t}.csv", mime="text/csv")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)  # fecha coluna direita

                # Limpa campos após processamento
                for g in group_table.keys():
                    st.session_state[f"seq_{g}"] = 0
            else:
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Aguardando upload de um arquivo para começar...", icon="👆")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # fecha main-container
