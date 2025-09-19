import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
import base64
import firebase_admin
from firebase_admin import credentials, db
import time

# --- CONFIGS ---
MAX_SEQ = 999_999

# --- CONEXÃO COM O FIREBASE (VERSÃO CORRIGIDA) ---
@st.cache_resource
def initialize_firebase():
    """Inicializa a conexão com o Firebase usando os Secrets do Streamlit."""
    if not firebase_admin._apps:
        # Pega as credenciais do secrets.toml
        creds_original = st.secrets["firebase_credentials"]
        
        # Cria uma cópia para podermos modificar
        creds_copy = dict(creds_original)
        
        # Modifica a cópia, e não o original
        creds_copy['private_key'] = creds_copy['private_key'].replace('\\n', '\n')
        
        # Usa a cópia modificada para autenticar
        cred = credentials.Certificate(creds_copy)
        databaseURL = creds_copy['databaseURL']
        
        firebase_admin.initialize_app(cred, {'databaseURL': databaseURL})
        
    return db.reference('sequentials')

db_ref = initialize_firebase()

# --- LINHA DE DEPURAÇÃO TEMPORÁRIA ---
# Esta linha ainda está aqui para nos ajudar a verificar se os segredos foram lidos.
st.write("Verificando segredos carregados:", st.secrets["firebase_credentials"])

# --- JSON helpers (agora usando o Firebase) ---
def load_sequentials_from_db():
    data = db_ref.get()
    if data:
        return data
    return {}

def save_sequentials_to_db(data):
    data_to_save = {k: int(v) for k, v in data.items()}
    db_ref.set(data_to_save)

# Colunas que o sistema espera e irá garantir que existam.
COLUNAS_OBRIGATORIAS = [
    'Nº DO ITEM', 'Nº DA PEÇA', 'TÍTULO', 'QTD.',
    'PROCESSO', 'GRUPO DE PRODUTO'
]

# --- Estilo ---
st.set_page_config(layout="wide", page_title="SolidWorks BOM Processor")
# ... (seu código de estilo CSS completo vai aqui) ...
st.markdown(f"""
<style>
    /* SEU CSS COMPLETO VAI AQUI */
</style>
""", unsafe_allow_html=True)


# --- FUNÇÕES DE LÓGICA (load_data, process_codes, etc.) ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, [], "Nenhum arquivo carregado."
    
    report_log = []
    df = None
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif name.endswith(".txt"):
            content = uploaded_file.getvalue().decode('utf-8').splitlines()
            header = [h.strip() for h in content[-1].split('\t')]
            data_lines = content[:-1]
            parsed_data = [
                (line.split('\t') + [''] * len(header))[:len(header)]
                for line in data_lines if line.strip()
            ]
            df = pd.DataFrame(parsed_data, columns=header)
            df = df.iloc[::-1].reset_index(drop=True)
        else:
            return None, [], "Formato de arquivo não suportado."

        colunas_originais = set(df.columns)
        colunas_obrigatorias_set = set(COLUNAS_OBRIGATORIAS)
        colunas_ausentes = colunas_obrigatorias_set - colunas_originais
        if colunas_ausentes:
            report_log.append(f"⚠️ Colunas ausentes (criadas vazias): **{', '.join(sorted(list(colunas_ausentes)))}**")
            for col in sorted(list(colunas_ausentes)):
                df[col] = ''

        ordem_final = COLUNAS_OBRIGATORIAS + sorted(list(colunas_originais - colunas_obrigatorias_set))
        df = df[ordem_final]
        df['QTD.'] = pd.to_numeric(df['QTD.'], errors='coerce').fillna(0)
        
        return df, report_log, "Arquivo lido com sucesso."
    except Exception as e:
        return None, [], f"Erro ao ler o arquivo: {e}"

def process_codes(df, sequentials, json_state, column_report):
    if df is None or df.empty:
        return pd.DataFrame(), [], "DataFrame vazio."

    report_log = list(column_report)
    report_log.append("--- Início do Processamento de Códigos ---")

    for g in list(sequentials.keys()):
        sequentials[g] = max(int(sequentials[g]), int(json_state.get(g, 0)))

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-(\d+)$')

    df['PROCESSO'] = df['PROCESSO'].astype(str).str.strip().str.upper()
    linhas_vazias = df['PROCESSO'].isin(['', 'NAN', None]) | pd.isna(df['PROCESSO'])
    
    count_preenchido = 0
    for i in df[linhas_vazias].index:
        is_manufactured = manufactured_pattern.match(str(df.loc[i, 'Nº DA PEÇA']))
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if is_manufactured else 'COMERCIAL'
        count_preenchido += 1
    
    if count_preenchido > 0:
        report_log.append(f"✔️ Coluna 'PROCESSO' preenchida para **{count_preenchido}** itens.")

    df['CÓDIGO FINAL'] = 'NULO'
    
    for _, row in df.iterrows():
        num = str(row.get('Nº DA PEÇA',''))
        m = commercial_pattern.match(num)
        if m:
            try:
                group, seq_str = num.split('-')
                sequentials[group] = max(sequentials.get(group, 0), int(seq_str))
            except: continue

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
            while f"{g}-{next_code:06d}" in df['CÓDIGO FINAL'].values:
                next_code += 1
            if next_code > MAX_SEQ:
                raise Exception(f"Limite de 6 dígitos atingido para o grupo {g}.")
            
            sequentials[g] = next_code
            new_code = f"{g}-{sequentials[g]:06d}"
            df.loc[i, 'CÓDIGO FINAL'] = new_code
            report_log.append(f"✔️ '{row.get('TÍTULO','')}' recebeu o código: {new_code}")
        else:
            report_log.append(f"⚠️ '{row.get('TÍTULO','')}' COMERCIAL sem grupo -> NULO")

    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()
    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts.pop()
            parent = '.'.join(parts)
            if parent in code_map: return code_map[parent]
        return ""
    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(find_parent_code)

    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    save_sequentials_to_db(sequentials)
    report_log.append("💾 Sequenciais atualizados no banco de dados online.")

    num_codes_generated = len([l for l in report_log if l.startswith("✔️ '")])
    report_log.insert(0, f"✅ Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")
    return df, report_log

@st.cache_data
def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Lista de Peças')
    return out.getvalue()


# --- Interface --- #
# (Todo o seu código de interface original vai aqui, sem alterações necessárias)
# ...
