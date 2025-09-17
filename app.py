import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# --- CONFIGS ---
STATE_FILE = "estado_sequenciais.json"
MAX_SEQ = 999_999  # 6 dígitos máximo

# --- Estilo (mantive sua paleta) ---
COLOR_PALETTE = {
    "dark_green": "#255000",
    "medium_green": "#588100",
    "lime_green": "#8db600",
    "light_yellow_green": "#c6da52",
    "dark_gray_text": "#434D36",
    "white": "#FFFFFF",
    "off_white_bg": "#F8F9FA",
    "light_gray_border": "#dee2e6",
    "button_hover": "#255000"
}

st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")

st.markdown(f"""
<style>
    .stApp {{ background-color: {COLOR_PALETTE["off_white_bg"]}; color: {COLOR_PALETTE["dark_gray_text"]}; }}
    .header-bar {{ background-color: {COLOR_PALETTE["dark_green"]}; padding: 10px 50px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .header-bar h1, .header-bar .stMarkdown p {{ color: {COLOR_PALETTE["white"]}; margin: 0; }}
    .card {{ background-color: {COLOR_PALETTE["white"]}; border: 1px solid {COLOR_PALETTE["light_gray_border"]}; border-radius: 10px; padding: 25px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); margin-bottom: 25px; }}
    .start-processing-section {{ background-color: {COLOR_PALETTE["lime_green"]}; padding: 40px; text-align: center; border-radius: 10px; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .stButton>button {{ background-color: {COLOR_PALETTE["medium_green"]}; color: {COLOR_PALETTE["white"]}; border-radius: 8px; border: none; padding: 10px 24px; font-weight: 500; transition: background-color 0.2s; }}
    .stButton>button:hover {{ background-color: {COLOR_PALETTE["button_hover"]}; color: {COLOR_PALETTE["white"]}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_PALETTE["light_yellow_green"]}; border-right: 1px solid #D9E1CC; }}
</style>
""", unsafe_allow_html=True)

@contextmanager
def card_container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    yield
    st.markdown('</div>', unsafe_allow_html=True)

# --- JSON helpers ---
def load_sequentials(file_path=STATE_FILE):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sequentials(data, file_path=STATE_FILE):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- load file helper ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, "Nenhum arquivo carregado."
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx"):
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

# --- process logic (mesma lógica, formato XXX-000001) ---
def process_codes(df, sequentials, json_state):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    report_log.append(f"ℹ️ Sequenciais informados (manual): {sequentials}")
    report_log.append(f"📂 Sequenciais (JSON): {json_state}")

    # usa o maior entre digitado e JSON
    for g in list(sequentials.keys()):
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')

    # preencher PROCESSO
    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row.get('Nº DA PEÇA',''))) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # atualiza sequenciais com base em códigos existentes na BOM
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA',''))
        m = commercial_pattern.match(num)
        if m:
            try:
                group = num.split('-')[0]
                seq = int(m.group(1))
                sequentials[group] = max(sequentials.get(group, 0), seq)
            except:
                continue
    report_log.append(f"Sequenciais depois de ler a BOM: {sequentials}")

    # gera códigos (XXX-000001)
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue

        num = str(row.get('Nº DA PEÇA',''))
        m_direct = commercial_pattern.match(num)
        if m_direct and len(m_direct.group(1)) == 6:
            df.loc[i, 'CÓDIGO FINAL'] = num
            continue

        m = group_pattern.search(str(row.get('GRUPO DE PRODUTO','')))
        if m:
            g = m.group(1)
            next_code = int(sequentials.get(g, 0)) + 1
            while True:
                if next_code > MAX_SEQ:
                    report_log.append(f"❌ Limite excedido para o grupo {g}. Sequencial alcançou {next_code} (> {MAX_SEQ}).")
                    raise Exception(f"Limite de 6 dígitos atingido para o grupo {g}.")
                candidate = f"{g}-{next_code:06d}"
                if candidate not in df['CÓDIGO FINAL'].values:
                    break
                next_code += 1
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
            report_log.append(f"✔️ '{row.get('TÍTULO','')}' recebeu código: {new_code}")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO','')}' COMERCIAL sem grupo -> NULO")

    # hierarquia pai-filho
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

    # ordena e uppercase
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    # salva JSON com os novos sequenciais
    save_sequentials({k:int(v) for k,v in sequentials.items()})
    report_log.append("💾 Sequenciais atualizados no estado_sequenciais.json")

    num_codes_generated = len([l for l in report_log if l.startswith("✔️")])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()

# --- Interface --- #
st.markdown("""
<div class="header-bar">
    <div>
        <h1>SolidWorks BOM Processor</h1>
        <p>Processamento automático de listas de materiais exportadas do SolidWorks</p>
    </div>
    <div class="header-nav">
        <p>⚡ Processamento Rápido</p>
        <p>📝 Normas Internas</p>
        <p>💾 Export Excel/CSV</p>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("1. Carregar Arquivo")
    uploaded_file = st.file_uploader("Selecione arquivo TXT ou XLSX", type=['txt','xlsx'])

# tabela de grupos
group_table = {
    "100": "Mecânico",
    "200": "Elétrico",
    "300": "Hidráulico Água",
    "400": "Hidráulico Óleo",
    "500": "Pneumático",
    "600": "Tecnologia",
    "700": "Infraestrutura",
    "800": "Insumos",
    "900": "Segurança",
    "950": "Serviço"
}

# carrega JSON antes de criar widgets
json_state = load_sequentials()

# versão para keys (permite "reset" criando novos keys)
if "version" not in st.session_state:
    st.session_state["version"] = 0

version = int(st.session_state["version"])

st.header("Tabela de Grupos – Próximo Código (6 dígitos máximo)")
cols = st.columns([1,2,2])
cols[0].markdown("**Grupo**")
cols[1].markdown("**Descrição**")
cols[2].markdown("**Próximo Código**")

# cria widgets com keys versionadas (não atribuímos session_state[...] = ...)
for g, desc in group_table.items():
    c0, c1, c2 = st.columns([1,2,2])
    c0.write(g)
    c1.write(desc)
    key = f"seq_{g}_v{version}"
    init_val = int(st.session_state.get(key, json_state.get(g, 0)))
    c2.number_input(
        f"Próximo código para grupo {g}",
        min_value=0,
        max_value=MAX_SEQ,
        value=init_val,
        step=1,
        key=key
    )

# callbacks
def increment_version():
    st.session_state["version"] = st.session_state.get("version", 0) + 1

# ações (botões)
st.markdown('<div class="start-processing-section">', unsafe_allow_html=True)
st.header("Começar Processamento")
st.write("Configure os grupos acima e clique em Processar.")
st.markdown('</div>', unsafe_allow_html=True)

c_proc, c_reset = st.columns([1,1])
process_clicked = c_proc.button("Processar")
reset_clicked = c_reset.button("Resetar inputs (limpar)")

if reset_clicked:
    increment_version()  # clicar o botão já causa rerun automático, então widgets serão recriados com nova versão

if process_clicked:
    # coleta sequenciais atuais do conjunto de widgets versionado
    sequentials = {g: int(st.session_state.get(f"seq_{g}_v{version}", 0)) for g in group_table.keys()}
    try:
        df_raw, msg = load_data(uploaded_file)
        if df_raw is None:
            st.error(msg)
        else:
            df_proc, report = process_codes(df_raw.copy(), sequentials, json_state)
            # salva resultados na sessão para exibir imediatamente
            st.session_state["last_report"] = report
            st.session_state["last_df_csv"] = df_proc.to_csv(index=False).encode("utf-8")
            st.session_state["last_df_excel"] = to_excel(df_proc)
            # sugerir ao usuário reset manual (opcional)
            st.success("Processamento concluído. Veja o relatório abaixo. Se quiser limpar os inputs, clique em 'Resetar inputs'.")
    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")

# mostra último relatório se existir
if st.session_state.get("last_report"):
    with card_container():
        st.subheader("Último Relatório de Processamento")
        for log in st.session_state["last_report"]:
            if log.startswith("✔️") or log.startswith("✅"):
                st.success(log)
            elif log.startswith("⚠️"):
                st.warning(log)
            elif log.startswith("❌"):
                st.error(log)
            else:
                st.info(log)

    # mostra tabela e permite download
    if st.session_state.get("last_df_csv"):
        df_show = pd.read_csv(io.BytesIO(st.session_state["last_df_csv"]))
        with card_container():
            st.subheader("Últimos Dados Processados")
            sort_option = st.radio("Classificar por:", ("Padrão","GRUPO DE PRODUTO","PROCESSO"), horizontal=True, key="last_sort_radio")
            df_display = df_show if sort_option=="Padrão" else df_show.sort_values(by=sort_option, kind='mergesort').reset_index(drop=True)
            st.dataframe(df_display, use_container_width=True)
            t = datetime.now().strftime("%Y%m%d_%H%M%S")
            c1,c2 = st.columns(2)
            with c1:
                st.download_button("📥 Baixar Excel", st.session_state["last_df_excel"], f"lista_codificada_{t}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with c2:
                st.download_button("📥 Baixar CSV", st.session_state["last_df_csv"], f"lista_codificada_{t}.csv", mime="text/csv")

st.markdown("---")
with card_container():
    st.markdown("<h2>Exportação</h2>", unsafe_allow_html=True)
    st.write("Os arquivos gravados ficam disponíveis para download após o processamento.")
