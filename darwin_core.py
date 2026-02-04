import pandas as pd
import io


def processar_dados_munguba(caminho_planilha_ocorrencias, dados_site_munguba):
    """
    Gera o ARQUIVO EXCEL (.xlsx) Darwin Core.
    Prioriza coordenadas do SITE (pontos_gps), depois tenta do Excel.
    """

    # --- 1. PREPARAR DADOS DO SITE ---
    df_site = pd.DataFrame(dados_site_munguba)

    # 1.1 EXTRAÇÃO DE LATITUDE E LONGITUDE DO SITE
    # O site tem uma lista [{'lat': -1.2, 'lng': -48.1}]. Vamos tirar isso de dentro da lista.
    def extrair_lat(pontos):
        if isinstance(pontos, list) and len(pontos) > 0:
            return points[0].get('lat', '')
        return ''

    def extrair_lng(pontos):
        if isinstance(pontos, list) and len(pontos) > 0:
            return points[0].get('lng', '')
        return ''

    # Cria colunas temporárias com as coordenadas do site
    if 'pontos_gps' in df_site.columns:
        df_site['lat_site'] = df_site['pontos_gps'].apply(
            lambda x: x[0].get('lat') if isinstance(x, list) and len(x) > 0 else '')
        df_site['lng_site'] = df_site['pontos_gps'].apply(
            lambda x: x[0].get('lng') if isinstance(x, list) and len(x) > 0 else '')
    else:
        df_site['lat_site'] = ''
        df_site['lng_site'] = ''

    # Cria chave de match
    if 'nome_cientifico' in df_site.columns:
        df_site['chave_match'] = df_site['nome_cientifico'].astype(str).str.lower().str.strip()
    else:
        return None, "Erro: Os dados do site não contêm o campo 'nome_cientifico'."

    # --- 2. CARREGAR EXCEL DE REFERÊNCIA ---
    try:
        df_excel = pd.read_excel(caminho_planilha_ocorrencias)
        col_match = 'species'
        if col_match not in df_excel.columns: col_match = 'acceptedScientificName'

        if col_match in df_excel.columns:
            df_excel['chave_match'] = df_excel[col_match].astype(str).str.lower().str.strip()
            df_excel = df_excel.drop_duplicates(subset=['chave_match'])
        else:
            df_excel = pd.DataFrame(columns=['chave_match'])

    except Exception as e:
        return None, f"Erro ao ler planilha Excel: {str(e)}"

    # --- 3. CRUZAMENTO (LEFT JOIN) ---
    # suffixes=('_site', '_excel') ajuda a diferenciar colunas com mesmo nome
    df_completo = pd.merge(df_site, df_excel, on='chave_match', how='left', suffixes=('_site', '_excel'))

    # --- 4. MAPEAMENTO DARWIN CORE ---
    df_dwc = pd.DataFrame()

    def get_val(row, col_prio, col_sec=None, padrao=''):
        val1 = row.get(col_prio)
        if pd.notna(val1) and str(val1).strip() != '': return val1
        if col_sec:
            val2 = row.get(col_sec)
            if pd.notna(val2) and str(val2).strip() != '': return val2
        return padrao

    df_dwc['scientificName'] = df_completo['nome_cientifico']

    # Family
    col_fam_exc = 'family_excel' if 'family_excel' in df_completo.columns else 'family'
    df_dwc['family'] = df_completo.apply(lambda x: get_val(x, col_fam_exc, 'familia'), axis=1)

    # Coordenadas: PRIORIDADE SITE (Gabarito) > Depois Excel GBIF
    # Atenção aos nomes das colunas vindas do Excel (decimalLatitude)
    df_dwc['decimalLatitude'] = df_completo.apply(lambda x: get_val(x, 'lat_site', 'decimalLatitude'), axis=1)
    df_dwc['decimalLongitude'] = df_completo.apply(lambda x: get_val(x, 'lng_site', 'decimalLongitude'), axis=1)

    # Demais campos taxonômicos (vêm do Excel)
    cols_excel = ['order', 'class', 'phylum', 'gbifID', 'basisOfRecord']
    for col in cols_excel:
        if col in df_completo.columns:
            df_dwc[col] = df_completo[col].fillna('')
        else:
            df_dwc[col] = ''

    df_dwc['genus'] = df_dwc['scientificName'].apply(lambda x: str(x).split()[0] if x else '')
    df_dwc['kingdom'] = 'Plantae'
    df_dwc['countryCode'] = 'BR'
    df_dwc['stateProvince'] = 'Pará'
    df_dwc['municipality'] = 'Belém'

    # Tratamento basisOfRecord
    df_dwc['basisOfRecord'] = df_dwc['basisOfRecord'].replace('', 'HumanObservation')

    # IDs
    indices = range(1, len(df_dwc) + 1)
    df_dwc['occurrenceID'] = [f"BRA:CESUPA:MUNGUBA:{i:04d}" for i in indices]

    # Ordenar
    df_dwc = df_dwc.sort_values(by='scientificName')

    # --- 5. EXPORTAR PARA EXCEL (BYTES) ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_dwc.to_excel(writer, index=False, sheet_name='Darwin Core')

        # Ajuste de largura das colunas
        ws = writer.sheets['Darwin Core']
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column_letter].width = min(adjusted_width, 50)

    output.seek(0)
    return output, None

def gerar_relatorio_comparativo(caminho_planilha_ocorrencias, dados_site_munguba):
    """
    Gera um Excel mostrando quais plantas do site foram encontradas na planilha de referência.
    """
    # 1. PREPARAR SITE
    lista_site = []
    for p in dados_site_munguba:
        nome_raw = str(p.get('nome_cientifico', '')).strip()
        lista_site.append({
            'Nome Site': nome_raw,
            'Chave Site': nome_raw.lower()
        })
    df_site = pd.DataFrame(lista_site)

    # 2. PREPARAR EXCEL DE REFERÊNCIA
    try:
        df_excel = pd.read_excel(caminho_planilha_ocorrencias)
        col_match = 'species'
        if col_match not in df_excel.columns:
            col_match = 'acceptedScientificName'

        if col_match in df_excel.columns:
            df_excel['chave_match'] = df_excel[col_match].astype(str).str.strip().str.lower()
            # Dicionário para busca rápida: chave -> nome original
            dict_excel = pd.Series(df_excel[col_match].values, index=df_excel['chave_match']).to_dict()
        else:
            dict_excel = {}

    except Exception as e:
        return None, f"Erro ao ler Excel: {str(e)}"

    # 3. COMPARAR
    resultados = []
    for _, row in df_site.iterrows():
        chave = row['Chave Site']
        if chave in dict_excel:
            resultados.append({
                "Nome Site": row['Nome Site'],
                "Status": "✅ Encontrado",
                "Correspondência Excel": dict_excel[chave]
            })
        else:
            resultados.append({
                "Nome Site": row['Nome Site'],
                "Status": "⚠️ Não encontrado",
                "Correspondência Excel": "-"
            })

    df_final = pd.DataFrame(resultados).sort_values(by='Status', ascending=True)  # Avisos primeiro

    # 4. EXPORTAR PARA EXCEL (BYTES)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Diagnostico')

        # Ajuste cosmético de largura de coluna (opcional)
        ws = writer.sheets['Diagnostico']
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 30

    output.seek(0)
    return output, None