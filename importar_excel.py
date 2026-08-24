import pandas as pd
import numpy as np
import os
from models import app, db, Taxon, Bioeconomico, Localizacao, Referencia, Occurrence

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_EXCEL = os.path.join(BASE_DIR, 'dados', 'BancoDados_munguba_Darwin_core.xlsx')


def safe_get(row, col_name):
    if col_name not in row: return None
    val = row[col_name]
    if pd.isna(val) or val is None: return None
    if isinstance(val, float) and np.isnan(val): return None
    if str(val).strip().lower() == 'nan' or str(val).strip() == '': return None
    return val


def importar_dados():
    print(f"📥 Lendo a planilha: {ARQUIVO_EXCEL}")

    try:
        df = pd.read_excel(ARQUIVO_EXCEL)
    except FileNotFoundError:
        print(f"❌ Erro: Arquivo não encontrado.")
        return

    total_linhas = len(df)
    print(f"📊 Encontradas {total_linhas} ocorrências. Iniciando importação...\n")

    with app.app_context():
        print("🧹 LIMPANDO O BANCO DE DADOS ANTIGO...")
        db.drop_all()
        db.create_all()
        print("✅ Limpeza concluída! Tabelas novas prontas para textos longos!\n")

        for index, row in df.iterrows():
            nome_cientifico = safe_get(row, 'scientificName')

            if not nome_cientifico:
                continue

            print(f"[{index + 1}/{total_linhas}] Processando: {nome_cientifico}...")

            taxon = Taxon.query.filter_by(scientificNameAccepted=nome_cientifico).first()
            if not taxon:
                taxon = Taxon(
                    scientificNameAccepted=nome_cientifico,
                    reino=safe_get(row, 'kingdom'),
                    filo=safe_get(row, 'phylum'),
                    classe=safe_get(row, 'class'),
                    ordem=safe_get(row, 'order'),
                    familia=safe_get(row, 'family'),
                    genero=safe_get(row, 'genus'),
                    especie=safe_get(row, 'species'),
                    taxonKey=safe_get(row, 'gbifId')
                )
                db.session.add(taxon)
                db.session.flush()

            bio = Bioeconomico.query.filter_by(id_taxon=taxon.id_taxon).first()
            if not bio:
                bio = Bioeconomico(
                    id_taxon=taxon.id_taxon,
                    nome_popular=safe_get(row, 'NOME POPULAR'),
                    origem_habitat=safe_get(row, 'ORIGEM E HABITAT'),
                    potencial_bioeconomico=safe_get(row, 'USO BIOECONOMICO'),
                    partes_planta=safe_get(row, 'PARTE DA PLANTA DE USO BIOECONOMICO'),
                    importancia=safe_get(row, 'Importância e aproveitamento na bioeconomia'),
                    referencias_bibliograficas=safe_get(row, 'BIBLIOGRAFIA DE POTENCIAL BIOECONOMICO')
                )
                db.session.add(bio)

            mun = safe_get(row, 'municipality')
            est = safe_get(row, 'stateProvince')
            loc = None
            if mun or est:
                loc = Localizacao.query.filter_by(municipio=mun, estado_provincia=est).first()
                if not loc:
                    loc = Localizacao(
                        codigo_pais=safe_get(row, 'countryCode'),
                        municipio=mun,
                        estado_provincia=est
                    )
                    db.session.add(loc)
                    db.session.flush()

            ref_texto = safe_get(row, 'reference')
            ref = None
            if ref_texto:
                ref = Referencia.query.filter_by(referencia=ref_texto).first()
                if not ref:
                    ref = Referencia(
                        referencia=ref_texto,
                        citacao_bibliografica=safe_get(row, 'bibliographicCitation')
                    )
                    db.session.add(ref)
                    db.session.flush()

            occ_id = safe_get(row, 'occurrenceID')
            if occ_id:
                occ_id = str(occ_id)
                ocorrencia = Occurrence.query.filter_by(occurrenceID=occ_id).first()
                if not ocorrencia:
                    ocorrencia = Occurrence(
                        occurrenceID=occ_id,
                        id_taxon=taxon.id_taxon,
                        id_localizacao=loc.id_localizacao if loc else None,
                        id_referencia=ref.id_referencia if ref else None,
                        scientificName=nome_cientifico,
                        kingdom=safe_get(row, 'kingdom'),
                        phylum=safe_get(row, 'phylum'),
                        class_=safe_get(row, 'class'),
                        order=safe_get(row, 'order'),
                        family=safe_get(row, 'family'),
                        genus=safe_get(row, 'genus'),
                        species=safe_get(row, 'species'),
                        gbifId=safe_get(row, 'gbifId'),
                        basisOfRecord=safe_get(row, 'basisOfRecord'),
                        decimalLatitude=safe_get(row, 'decimalLatitude'),
                        decimalLongitude=safe_get(row, 'decimalLongitude'),
                        eventDate=safe_get(row, 'eventDate'),
                        iucnRedListCategory=safe_get(row, 'iucnRedListCategory'),
                        reference=safe_get(row, 'reference'),
                        bibliographicCitation=safe_get(row, 'bibliographicCitation'),
                        countryCode=safe_get(row, 'countryCode'),
                        municipality=safe_get(row, 'municipality'),
                        stateProvince=safe_get(row, 'stateProvince')
                    )
                    db.session.add(ocorrencia)

        db.session.commit()
        print("\n✨ SUCESSO! A planilha inteira foi jogada pro MySQL!")


if __name__ == '__main__':
    importar_dados()