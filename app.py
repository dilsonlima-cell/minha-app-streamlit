def process_codes(df, state_file):
    if df is None or df.empty:
        return pd.DataFrame(), []

    report_log = []
    sequentials = load_sequentials(state_file)
    report_log.append(f"Estado sequenciais carregado: {sequentials or 'Nenhum'}")

    group_pattern = re.compile(r'(\d{3})')
    manufactured_pattern = re.compile(r'^\d{2}-\d{4}-\d{4}-.*')
    commercial_pattern = re.compile(r'^\d{3}-\d{4}$')

    # --- Preencher coluna PROCESSO se estiver vazia ---
    processed_count = 0
    for i, row in df.iterrows():
        if not row['PROCESSO'].strip():
            df.loc[i, 'PROCESSO'] = (
                'FABRICADO' if manufactured_pattern.match(str(row['Nº DA PEÇA'])) else 'COMERCIAL'
            )
            processed_count += 1
    report_log.append(f"Coluna 'PROCESSO' preenchida para {processed_count} linhas vazias.")

    # --- Inicializar coluna de códigos ---
    df['CÓDIGO FINAL'] = ''

    # --- Ajustar sequenciais iniciais (para comerciais já codificados) ---
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
    report_log.append(f"Sequenciais iniciais ajustados: {sequentials or 'Nenhum'}")

    # --- Definir CÓDIGO FINAL ---
    for i, row in df.iterrows():
        processo = row['PROCESSO']
        num = str(row['Nº DA PEÇA'])

        # FABRICADO, MONTAGEM e SOLDA usam diretamente o código da peça se válido
        if processo in ['FABRICADO', 'MONTAGEM', 'SOLDA']:
            if manufactured_pattern.match(num):
                df.loc[i, 'CÓDIGO FINAL'] = num
            else:
                # gerar código sequencial se não houver nº de peça válido
                m = group_pattern.search(str(row['GRUPO DE PRODUTO']))
                if m:
                    g = m.group(1)
                    sequentials[g] = sequentials.get(g, 0) + 1
                    new_code = f"{g}-{sequentials[g]:04d}"
                    df.loc[i, 'CÓDIGO FINAL'] = new_code
                    report_log.append(f"'{row['TÍTULO']}' recebeu código: {new_code}")
                else:
                    df.loc[i, 'CÓDIGO FINAL'] = 'NULO'
            continue

        # COMERCIAL
        if processo == 'COMERCIAL':
            if commercial_pattern.match(num):
                df.loc[i, 'CÓDIGO FINAL'] = num
                continue
            m = group_pattern.search(str(row['GRUPO DE PRODUTO']))
            if m:
                g = m.group(1)
                sequentials[g] = sequentials.get(g, 0) + 1
                new_code = f"{g}-{sequentials[g]:04d}"
                df.loc[i, 'CÓDIGO FINAL'] = new_code
                report_log.append(f"'{row['TÍTULO']}' recebeu código: {new_code}")
            else:
                df.loc[i, 'CÓDIGO FINAL'] = 'NULO'
                report_log.append(f"'{row['TÍTULO']}' COMERCIAL sem grupo -> NULO")

    df['CÓDIGO FINAL'] = df['CÓDIGO FINAL'].replace('', 'NULO')

    # --- Ordenação lógica ---
    def get_tipo(row):
        if row['CÓDIGO FINAL'] != 'NULO':
            return 1
        return 2
    df['TIPO'] = df.apply(get_tipo, axis=1)
    df = df.sort_values(by=['TIPO', 'CÓDIGO FINAL']).drop(columns=['TIPO']).reset_index(drop=True)

    # --- Padronizar strings ---
    for col in df.select_dtypes(include=['object']):
        df[col] = df[col].astype(str).str.upper()

    # --- Construir hierarquia PAI/FILHO ---
    df['Nº DO ITEM'] = df['Nº DO ITEM'].astype(str).str.strip()
    code_map = pd.Series(df['CÓDIGO FINAL'].values, index=df['Nº DO ITEM']).to_dict()

    def find_parent_code(item_id):
        parts = item_id.split('.')
        while len(parts) > 1:
            parts = parts[:-1]
            parent = '.'.join(parts)
            if parent in code_map and code_map[parent] != 'NULO':
                return code_map[parent]
        return None

    df['CÓDIGO PAI'] = df['Nº DO ITEM'].apply(lambda x: find_parent_code(x) or '')

    # --- Herança de código para pais com NULO mas filhos válidos ---
    for i, row in df.iterrows():
        if row['CÓDIGO FINAL'] == 'NULO':
            filhos = [cid for cid in df['Nº DO ITEM'] if cid.startswith(row['Nº DO ITEM'] + '.')]
            if filhos:
                filho_codigo = df.loc[df['Nº DO ITEM'] == filhos[0], 'CÓDIGO FINAL'].values[0]
                if filho_codigo != 'NULO':
                    df.loc[i, 'CÓDIGO FINAL'] = filho_codigo
                    report_log.append(f"'{row['TÍTULO']}' herdou código do filho: {filho_codigo}")

    # --- Reordenamento de colunas ---
    cols = df.columns.tolist()
    final_order = [
        col for col in [
            'Nº DO ITEM', 'TÍTULO', 'Nº DA PEÇA', 'PROCESSO',
            'GRUPO DE PRODUTO', 'MATERIAL', 'DIMENSÕES',
            'CÓDIGO FINAL', 'CÓDIGO PAI'
        ] if col in cols
    ]
    other_cols = [col for col in cols if col not in final_order]
    df = df[final_order + other_cols]

    # --- Salvar estado ---
    save_sequentials(state_file, sequentials)
    report_log.append(f"Sequenciais salvos em {state_file}")
    num_codes_generated = len([log for log in report_log if 'recebeu código:' in log])
    report_log.insert(0, f"Processamento concluído. {num_codes_generated} novos códigos comerciais foram gerados.")

    return df, report_log
