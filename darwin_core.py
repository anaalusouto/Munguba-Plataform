import pandas as pd
import io


def processar_dados_munguba(caminho_planilha_ocorrencias, dados_site_munguba):
    """
    Gera o Darwin Core priorizando as espécies do SITE.
    Usa a coluna 'species' do Excel para fazer o cruzamento (match).
    """

    # --- 1. PREPARAR DADOS DO SITE (Principal) ---
    df_site = pd.DataFrame(dados_site_munguba)

    # Chave do Site: nome_cientifico limpo
    if 'nome_cientifico' in df_site.columns:
        df_site['chave_match'] = df_site['nome_cientifico'].astype(str).str.lower().str.strip()
    else:
        return None, "Erro: Dados do site não contêm 'nome_cientifico'."

    # --- 2. CARREGAR DADOS DO EXCEL (Enriquecimento) ---
    try:
        df_excel = pd.read_excel(caminho_planilha_ocorrencias)

        # --- ALTERAÇÃO AQUI: USAR COLUNA 'SPECIES' ---
        col_match_excel = 'species'  # Nome da coluna no Excel que vamos usar

        # Verifica se a coluna existe, senão tenta achar acceptedScientificName como fallback
        if col_match_excel not in df_excel.columns:
            print(f"Aviso: Coluna '{col_match_excel}' não encontrada. Tentando 'acceptedScientificName'.")
            col_match_excel = 'acceptedScientificName'

        if col_match_excel in df_excel.columns:
            # Cria a chave de busca baseada na coluna SPECIES
            df_excel['chave_match'] = df_excel[col_match_excel].astype(str).str.lower().str.strip()
        else:
            # Se não tiver nenhuma das duas, cria vazio
            df_excel = pd.DataFrame(columns=['chave_match'])

    except FileNotFoundError:
        df_excel = pd.DataFrame(columns=['chave_match'])
    except Exception as e:
        return None, f"Erro ao ler Excel: {str(e)}"

    # --- 3. CRUZAMENTO (LEFT JOIN) ---
    # Remove duplicatas do Excel (se houver várias linhas da mesma espécie, pega a primeira)
    if not df_excel.empty:
        df_excel_unicos = df_excel.drop_duplicates(subset=['chave_match'])
        df_completo = pd.merge(df_site, df_excel_unicos, on='chave_match', how='left', suffixes=('_site', '_excel'))
    else:
        df_completo = df_site
        # Adiciona colunas vazias para não quebrar o código abaixo
        for col in ['family', 'genus', 'order', 'class', 'phylum', 'gbifId', 'decimalLatitude', 'decimalLongitude']:
            df_completo[col] = ''

    # --- 4. MAPEAMENTO DARWIN CORE ---
    df_dwc = pd.DataFrame()

    def get_val(row, col_excel, col_site=None, fallback=''):
        val_excel = row.get(col_excel)
        val_site = row.get(col_site)

        if pd.notna(val_excel) and str(val_excel).strip() != '':
            return val_excel
        if col_site and pd.notna(val_site) and str(val_site).strip() != '':
            return val_site
        return fallback

    # Scientific Name (Prioridade Site)
    df_dwc['scientificName'] = df_completo['nome_cientifico']

    # Family (Prioridade Excel > Site)
    # Nota: No merge, se tiver colunas iguais, o pandas cria 'family_excel' e 'family_site'.
    # O get_val precisa lidar com isso, mas como usamos suffixes, vamos verificar:
    col_familia_excel = 'family' if 'family' in df_completo.columns else 'family_excel'
    df_dwc['family'] = df_completo.apply(lambda x: get_val(x, col_familia_excel, 'familia'), axis=1)

    # Genus
    def extrair_genero(row):
        val_excel = row.get('genus')
        if pd.notna(val_excel) and str(val_excel).strip() != '':
            return val_excel
        nome = str(row.get('nome_cientifico', '')).strip()
        if nome:
            return nome.split()[0]
        return ''

    df_dwc['genus'] = df_completo.apply(extrair_genero, axis=1)

    # Kingdom (= Genus)
    df_dwc['kingdom'] = df_dwc['genus']

    # Colunas Exclusivas do Excel
    cols_excel_only = ['order', 'class', 'phylum', 'gbifId', 'basisOfRecord',
                       'decimalLatitude', 'decimalLongitude', 'eventDate', 'iucnRedListCategory']

    for col in cols_excel_only:
        if col in df_completo.columns:
            df_dwc[col] = df_completo[col].fillna('')
        else:
            df_dwc[col] = ''

    # Reference / Bibliografia
    if 'reference' in df_completo.columns:
        df_dwc['reference'] = df_completo['reference'].fillna('')
    elif 'bibliografia' in df_completo.columns:
        df_dwc['reference'] = df_completo['bibliografia'].fillna('')
    else:
        df_dwc['reference'] = ''

    # --- 5. CAMPOS FIXOS ---
    df_dwc['countryCode'] = 'BR'
    df_dwc['municipality'] = 'Belém'
    df_dwc['stateProvince'] = 'Pará'

    df_dwc['basisOfRecord'] = df_dwc['basisOfRecord'].replace('', 'HUMAN_OBSERVATION')

    # --- 6. ORDENAÇÃO E ID ---
    df_dwc = df_dwc.sort_values(by='scientificName', ascending=True)

    indices = range(1, len(df_dwc) + 1)
    df_dwc['occurrenceID'] = [f"BRA:CESUPA:PPGITS:{i:05d}" for i in indices]

    # --- 7. EXPORTAÇÃO ---
    return df_dwc.to_csv(index=False, encoding='utf-8-sig', sep=','), None


# --- FUNÇÃO DE DIAGNÓSTICO ATUALIZADA TAMBÉM ---
def gerar_relatorio_comparativo(caminho_planilha_ocorrencias, dados_site_munguba):
    import pandas as pd
    import io

    # 1. SITE
    lista_site = []
    for p in dados_site_munguba:
        nome_raw = str(p.get('nome_cientifico', '')).strip()
        lista_site.append({
            'Nome Site': nome_raw,
            'Chave Site': nome_raw.lower()
        })
    df_site = pd.DataFrame(lista_site)

    # 2. EXCEL (USANDO SPECIES)
    try:
        df_excel = pd.read_excel(caminho_planilha_ocorrencias)
        col_match = 'species'  # Definindo explicitamente

        if col_match not in df_excel.columns:
            return None, f"Coluna '{col_match}' não encontrada no Excel para diagnóstico."

        df_excel['Chave Excel'] = df_excel[col_match].astype(str).str.strip().str.lower()
        # Dicionário reverso para mostrar qual nome bateu
        dict_excel = pd.Series(df_excel[col_match].values, index=df_excel['Chave Excel']).to_dict()

    except Exception as e:
        return None, f"Erro ao ler Excel: {str(e)}"

    # 3. COMPARAR
    resultados = []
    for index, row in df_site.iterrows():
        chave = row['Chave Site']
        if chave in dict_excel:
            resultados.append({
                "Nome Site": row['Nome Site'],
                "Status": "✅ Encontrado (via species)",
                "Nome Excel": dict_excel[chave]
            })
        else:
            resultados.append({
                "Nome Site": row['Nome Site'],
                "Status": "⚠️ Não encontrado",
                "Nome Excel": "-"
            })

    df_final = pd.DataFrame(resultados).sort_values(by='Status', ascending=False)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Diagnostico_Species')
    output.seek(0)
    return output, None