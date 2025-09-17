import streamlit as st
import pandas as pd
import io
import re
import json
import os
from datetime import datetime
from contextlib import contextmanager

# -------------------------
# Configurações de estado
# -------------------------
ESTADO_FILE = "estado_sequenciais.json"

def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_estado(sequentials):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(sequentials, f, ensure_ascii=False, indent=4)

def verificar_duplicatas(df, estado):
    duplicatas = []
    codigos_existentes = set()
    for grupo, ultimo_seq in estado.items():
        for seq in range(1, ultimo_seq + 1):
            codigos_existentes.add(f"{grupo}-{str(seq).zfill(6)}")
    for codigo in df['Nº DA PEÇA'].astype(str):
        if codigo in codigos_existentes:
            duplicatas.append(codigo)
    return duplicatas

# -------------------------
# Função de processamento
# -------------------------
def process_codes(df, sequentials):
    if df is None or df.empty:
        return pd.DataFrame(), [], 0

    estado_atual = carregar_estado()
    for g in sequentials:
        sequentials[g] = max(sequentials[g], estado_atual.get(g, 0))

    report_log = []
    report_log.append(f"ℹ️ Sequenciais carregados: {sequentials}")

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{6}$')

    for i, row in df.iterrows():
        df.loc[i, 'PROCESSO'] = 'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
    report_log.append("Coluna 'PROCESSO' preenchida automaticamente.")

    df['CÓDIGO FINAL'] = 'NULO'

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
    report_log.append(f"Sequenciais ajustados com base no arquivo: {sequentials}")

    novos_codigos = 0
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
                new_code = f"{g}-{str(sequentials[g]).zfill(6)}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                novos_codigos += 1
                report_log.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                report_log.append(f"⚠️ '{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

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
    report_log.append("Hierarquia pai-filho processada.")

    def get_tipo(row):
        if row['PROCESSO'] == 'FABRICADO': return 1
        if row['PROCESSO'] == 'COMERCIAL' and row['CÓDIGO FINAL'] != 'NULO': return 2
        return 3
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO','CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)

    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    report_log.insert(0, f"✅ Processamento concluído. {novos_codigos} novos códigos comerciais foram gerados.")

    return df, report_log, novos_codigos

# -------------------------
# Interface Streamlit
# -------------------------
st.title("Gerador de Códigos Sequenciais")

# Mostra contador de códigos já existentes no histórico
estado_atual = carregar_estado()
total_existentes = sum(estado_atual.values())
st.info(f"📊 Histórico: {total_existentes} códigos já registrados.")

uploaded_file = st.file_uploader("Envie seu arquivo Excel", type=["xlsx"])
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)

    duplicatas = verificar_duplicatas(df_raw, estado_atual)
    if duplicatas:
        st.error(f"🚫 Arquivo contém códigos já existentes: {', '.join(duplicatas)}")
    else:
        grupos = sorted(set(re.findall(r'\d{3}', " ".join(df_raw['GRUPO DE PRODUTO'].astype(str)))))
        sequentials = {}
        for g in grupos:
            sequentials[g] = st.number_input(
                f"Último sequencial para o grupo {g}",
                min_value=0,
                value=estado_atual.get(g, 0),
                step=1,
                key=f"seq_{g}"
            )

        if st.button("Processar Lista"):
            df_proc, report, novos = process_codes(df_raw.copy(), sequentials)

            # Atualiza contador após processamento
            total_atualizado = sum(carregar_estado().values())
            st.success(f"📈 Histórico atualizado: {total_atualizado} códigos no total (+{novos} novos).")

            for r in report:
                st.success(r)
            st.dataframe(df_proc)

            for g in grupos:
                st.session_state[f"seq_{g}"] = 0
