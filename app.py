import streamlit as st
import pandas as pd
import json
import os
import re

# -------------------------------
# Configurações iniciais
# -------------------------------
st.set_page_config(page_title="SolidWorks BOM Processor", layout="wide")

STATE_FILE = "estado_sequenciais.json"

MANDATORY_COLS = ["Nº DA PEÇA", "PROCESSO", "GRUPO DE PRODUTO", "TÍTULO", "Nº DO ITEM"]

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
    "950": "Serviço",
}

# -------------------------------
# Funções auxiliares
# -------------------------------
def load_sequentials(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_sequentials(state_file, data):
    with open(state_file, "w") as f:
        json.dump(data, f, indent=4)

# -------------------------------
# Leitura dos dados
# -------------------------------
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is None:
        return None, ["Nenhum arquivo carregado."]

    logs = []
    try:
        name = uploaded_file.name.lower()
        if name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:  # TXT
            content = uploaded_file.getvalue().decode("utf-8").splitlines()
            header = [h.strip() for h in content[-1].split("\t")]
            data_lines = content[:-1]
            parsed_data = []
            for line in data_lines:
                if line.strip():
                    cells = [cell.strip() for cell in line.split("\t")]
                    while len(cells) < len(header):
                        cells.append("")
                    parsed_data.append(cells[: len(header)])
            df = pd.DataFrame(parsed_data, columns=header)
            df = df.iloc[::-1].reset_index(drop=True)

        # Verificar colunas obrigatórias
        for col in MANDATORY_COLS:
            if col not in df.columns:
                df[col] = ""
                logs.append(f"⚠️ Coluna obrigatória '{col}' não encontrada, criada vazia.")

        # Colunas extras
        extras = [c for c in df.columns if c not in MANDATORY_COLS]
        if extras:
            logs.append(f"ℹ️ Colunas adicionais detectadas e mantidas: {extras}")

        return df, logs
    except Exception as e:
        return None, [f"Erro ao ler o arquivo: {e}"]

# -------------------------------
# Processamento dos códigos
# -------------------------------
def process_codes(df, sequentials, state_file):
    logs = []
    df["CÓDIGO FINAL"] = ""

    manufactured_pattern = re.compile(r"^\d{2}-\d{4}-\d{4}-\d{3}-\d{2}$")
    commercial_pattern = re.compile(r"^\d{3}-\d{4}$")
    group_pattern = re.compile(r"(\d{3})")

    # Carregar últimos sequenciais salvos
    last_saved = load_sequentials(state_file)

    # Preencher PROCESSO somente onde estiver vazio
    for i, row in df.iterrows():
        if str(row["PROCESSO"]).strip() == "":
            if manufactured_pattern.match(str(row["Nº DA PEÇA"])):
                df.loc[i, "PROCESSO"] = "FABRICADO"
            else:
                df.loc[i, "PROCESSO"] = "COMERCIAL"

    # Gerar códigos
    for i, row in df.iterrows():
        proc = str(row["PROCESSO"]).strip()
        numpeca = str(row["Nº DA PEÇA"]).strip()

        if proc == "FABRICADO":
            df.loc[i, "CÓDIGO FINAL"] = numpeca
            continue

        if proc == "COMERCIAL":
            if commercial_pattern.match(numpeca):
                df.loc[i, "CÓDIGO FINAL"] = numpeca
                continue

            m = group_pattern.search(str(row["GRUPO DE PRODUTO"]))
            if m:
                g = m.group(1)

                # Pega maior entre informado manualmente e salvo
                base_seq = max(int(sequentials.get(g, 0)), int(last_saved.get(g, 0)))
                next_code = base_seq + 1

                # Evitar repetição dentro do próprio DataFrame
                while f"{g}-{next_code:06d}" in df["CÓDIGO FINAL"].values:
                    next_code += 1

                # Limitar a 6 dígitos
                if next_code > 999999:
                    logs.append(f"❌ Limite de 6 dígitos atingido no grupo {g}.")
                    continue

                sequentials[g] = next_code
                new_code = f"{g}-{next_code:06d}"
                df.loc[i, "CÓDIGO FINAL"] = new_code
                logs.append(f"✔️ '{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                logs.append(f"⚠️ '{row['TÍTULO']}' sem grupo válido -> NULO")

    # Atualizar arquivo de estado
    save_sequentials(state_file, sequentials)

    return df, logs

# -------------------------------
# Interface Streamlit
# -------------------------------
st.markdown("<h1 style='color: darkgreen;'>SolidWorks BOM Processor</h1>", unsafe_allow_html=True)
st.caption("Processamento automático de listas de materiais exportadas do SolidWorks")

# Upload
uploaded_file = st.sidebar.file_uploader("Selecione arquivo TXT ou XLSX", type=["txt", "xlsx"])

# Configuração de grupos
st.header("Tabela de Grupos – Próximo Código (6 dígitos máximo)")

sequentials = {}
cols = st.columns([1, 2, 2])
cols[0].markdown("**Grupo**")
cols[1].markdown("**Descrição**")
cols[2].markdown("**Próximo Código**")

for g, desc in group_table.items():
    c1, c2, c3 = st.columns([1, 2, 2])
    c1.write(g)
    c2.write(desc)
    sequentials[g] = c3.number_input(
        f"Próximo código para grupo {g}",
        min_value=0,
        max_value=999999,
        value=0,
        step=1,
        key=f"seq_{g}",
    )

st.markdown("---")
st.subheader("Começar Processamento")
st.caption("Faça upload do arquivo TXT/XLSX exportado do SolidWorks e configure os grupos acima.")

if uploaded_file is not None:
    df, load_logs = load_data(uploaded_file)

    if df is not None:
        if st.button("▶️ Processar Lista"):
            df_proc, report = process_codes(df, sequentials, STATE_FILE)

            # Mostrar relatório
            st.success("Processamento concluído!")
            with st.expander("📋 Relatório de processamento"):
                for log in load_logs + report:
                    st.write(log)

            # Mostrar tabela processada
            st.dataframe(df_proc, use_container_width=True)

            # Exportação
            st.download_button("⬇️ Exportar Excel", df_proc.to_csv(index=False).encode("utf-8"), "saida.csv", "text/csv")

else:
    st.info("Carregue um arquivo TXT ou XLSX para iniciar.")

