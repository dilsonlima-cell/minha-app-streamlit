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

# --- Estética (mantive a sua paleta/estilo) ---
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

# --- Funções JSON ---
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

# --- Leitura de arquivo TXT/XLSX ---
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
        # assume cabeçalho na última linha (como seu arquivo de exemplo)
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

# --- Processamento dos códigos ---
def process_codes(df, sequentials, json_state):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    report_log.append(f"ℹ️ Sequenciais informados (manual): {sequentials}")
    report_log.append(f"📂 Sequenciais (JSON): {json_state}")

    # Prioriza o maior entre digitado e JSON
    for g in list(sequentials.keys()):
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    # aceitar quaisquer dígitos após o hífen para ler sequenciais antigos; geraremos novos com 6 dígitos fixos
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')

    # preencher PROCESSO
    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row.get('Nº DA PEÇA',''))) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

    # Ajusta sequenciais com base nos códigos já existentes na BOM (qualquer comprimento de sequencial)
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

    # Geração dos códigos (formato XXX-000001, 6 dígitos) garantindo unicidade e limite
    for i, row in df.iterrows():
        if row['PROCESSO'] == 'FABRICADO':
            df.loc[i, 'CÓDIGO FINAL'] = row.get('Nº DA PEÇA', '')
            continue

        num = str(row.get('Nº DA PEÇA',''))
        m_direct = commercial_pattern.match(num)
        if m_direct and len(m_direct.group(1)) == 6:
            # já está no formato 6 dígitos
            df.loc[i, 'CÓDIGO FINAL'] = num
            continue

        m = group_pattern.search(str(row.get('GRUPO DE PRODUTO','')))
        if m:
            g = m.group(1)
            next_code = int(sequentials.get(g, 0)) + 1
            # procura próximo código livre, mas respeita o limite de 6 dígitos
            while True:
                if next_code > MAX_SEQ:
                    report_log.append(f"❌ Limite excedido para o grupo {g}. Sequencial alcançou {next_code} (> {MAX_SEQ}).")
                    raise Exception(f"Limite de 6 dígitos atingido para o grupo {g}. Pare a operação e reveja o estado.")
                candidate = f"{g}-{next_code:06d}"
                # não gerar duplicado considerando códigos já atribuídos
                if candidate not in df['CÓDIGO FINAL'].values:
                    break
                next_code += 1
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
            report_log.append(f"✔️ '{row.get('TÍTULO','')}' recebeu código: {new_code}")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO','')}' COMERCIAL sem grupo -> NULO")

    # Hierarquia pai-filho (procura código do pai pelo Nº DO ITEM)
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

    # Ordenação e formatação
    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    # salvar estado final no JSON (sequenciais são numéricos)
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

# tabela de grupos (norma)
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

# Carrega estado JSON antes de criar widgets
json_state = load_sequentials()

# Se foi solicitada limpeza (flag), faça o reset ANTES de criar os widgets
if st.session_state.get("reset_after_process", False):
    for g in group_table.keys():
        st.session_state[f"seq_{g}"] = 0
    st.session_state["reset_after_process"] = False  # limpa flag

# Inicializa chaves no session_state com valores do JSON se ainda não existirem
for g in group_table.keys():
    key = f"seq_{g}"
    if key not in st.session_state:
        st.session_state[key] = int(json_state.get(g, 0))

st.header("Tabela de Grupos – Próximo Código (6 dígitos máximo)")
cols = st.columns([1,2,2])
cols[0].markdown("**Grupo**")
cols[1].markdown("**Descrição**")
cols[2].markdown("**Próximo Código**")

# cria widgets ligados a session_state (valor inicial vem do session_state)
for g, desc in group_table.items():
    c0, c1, c2 = st.columns([1,2,2])
    c0.write(g)
    c1.write(desc)
    # limite máximo = 999999 (6 dígitos)
    st.session_state[f"seq_{g}"] = c2.number_input(
        f"Próximo código para grupo {g}",
        min_value=0,
        max_value=MAX_SEQ,
        value=int(st.session_state.get(f"seq_{g}", 0)),
        step=1,
        key=f"seq_{g}"
    )

st.markdown('<div class="start-processing-section">', unsafe_allow_html=True)
st.header("Começar Processamento")
st.write("Faça upload do arquivo TXT/XLSX exportado do SolidWorks e configure os grupos acima.")
st.markdown('</div>', unsafe_allow_html=True)

if not uploaded_file:
    st.info("Aguardando upload de um arquivo para começar...", icon="👆")
else:
    try:
        with st.spinner("Processando..."):
            df_raw, msg = load_data(uploaded_file)
            if df_raw is None:
                st.error(f"❌ {msg}")
            else:
                # cria dicionário de sequenciais baseado nos valores dos widgets (session_state)
                sequentials = {g: int(st.session_state.get(f"seq_{g}", 0)) for g in group_table.keys()}
                df_proc, report = process_codes(df_raw.copy(), sequentials, json_state)

                # após processamento: sinalizar reset e reiniciar (para limpar widgets sem erro)
                st.session_state["reset_after_process"] = True
                # mostra relatório antes de reiniciar: (salva em sessão para mostrar na próxima execução)
                st.session_state["last_report"] = report
                st.experimental_rerun()

    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

# Se existir relatório guardado (vindo de uma execução anterior), mostre-o
if st.session_state.get("last_report"):
    with card_container():
        st.subheader("Último Relatório de Processamento")
        for log in st.session_state.get("last_report", []):
            if "✔️" in log or "✅" in log: st.success(log)
            elif "⚠️" in log: st.warning(log)
            elif "❌" in log: st.error(log)
            else: st.info(log)
    # opcional: botão para limpar exibição do relatório
    if st.button("Limpar relatório exibido"):
        st.session_state["last_report"] = None
        st.experimental_rerun()

# Rodapé / Export
st.markdown("---")
with card_container():
    st.markdown("<h2>Exportação</h2>", unsafe_allow_html=True)
    st.write("Os arquivos gerados ficam disponíveis para download após o processamento (na próxima execução).")
