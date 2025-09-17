import streamlit as st
import pandas as pd
import re
import json
import os

ESTADO_FILE = "estado_sequenciais.json"

# -------------------------
# Funções de persistência
# -------------------------
def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_estado(sequentials):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(sequentials, f, ensure_ascii=False, indent=4)

# -------------------------
# Função para verificar duplicatas
# -------------------------
def verificar_duplicatas(df, estado):
    duplicatas = []
    # Gera lista de todos os códigos já existentes no estado
    codigos_existentes = set()
    for grupo, ultimo_seq in estado.items():
        for seq in range(1, ultimo_seq + 1):
            codigos_existentes.add(f"{grupo}-{str(seq).zfill(6)}")

    # Verifica se algum código do arquivo já está no estado
    for codigo in df['Nº DA PEÇA'].astype(str):
        if codigo in codigos_existentes:
            duplicatas.append(codigo)

    return duplicatas

# -------------------------
# Função principal de processamento
# -------------------------
def process_codes(df, sequentials):
    estado_atual = carregar_estado()

    # Garante que o sequencial inicial seja o maior entre digitado e salvo
    for g in sequentials:
        sequentials[g] = max(sequentials[g], estado_atual.get(g, 0))

    for i, row in df.iterrows():
        if row['PROCESSO'] == 'COMERCIAL':
            num = str(row['Nº DA PEÇA'])
            # Se já estiver no formato correto, mantém
            if not re.match(r'^\d{3}-\d{6}$', num):
                m = re.search(r'(\d{3})', str(row['GRUPO DE PRODUTO']))
                if m:
                    g = m.group(1)
                    sequentials[g] = sequentials.get(g, 0) + 1
                    new_code = f"{g}-{str(sequentials[g]).zfill(6)}"
                    df.loc[i, 'CÓDIGO FINAL'] = new_code
                else:
                    df.loc[i, 'CÓDIGO FINAL'] = "NULO"
            else:
                df.loc[i, 'CÓDIGO FINAL'] = num

    # Salva estado atualizado
    salvar_estado(sequentials)

    return df, ["✅ Processamento concluído e estado salvo."]

# -------------------------
# Interface Streamlit
# -------------------------
st.title("Gerador de Códigos Sequenciais")

# Upload do arquivo
uploaded_file = st.file_uploader("Envie seu arquivo Excel", type=["xlsx"])
if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)

    # Carrega estado atual
    estado_atual = carregar_estado()

    # Verifica duplicatas antes de mostrar inputs
    duplicatas = verificar_duplicatas(df_raw, estado_atual)
    if duplicatas:
        st.error(f"🚫 Arquivo contém códigos já existentes: {', '.join(duplicatas)}")
    else:
        # Identifica grupos únicos
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
            df_proc, report = process_codes(df_raw.copy(), sequentials)

            # Mostra relatório
            for r in report:
                st.success(r)

            st.dataframe(df_proc)

            # Limpa campos após processamento
            for g in grupos:
                st.session_state[f"seq_{g}"] = 0
