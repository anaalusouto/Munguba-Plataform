# Munguba Platform: Bioeconomy and Biodiversity System of the Combu Island APA

**Munguba** is a web-based application designed to catalog, visualize, and standardize data on floristic species with bioeconomic value in the Amazon. The project integrates technology and Open Science, promoting the valorization of local flora through geospatial visualizations and data interoperability based on the Darwin Core (DwC) standard.

## Overview

This project applies the **FAIR Principles** (Findable, Accessible, Interoperable, Reusable) to species occurrence data. The platform allows researchers and the community to visualize species distribution on Combu Island and access standardized data compliant with international biodiversity informatics standards.

## Features

* **Interactive Mapping:** Leaflet/OpenStreetMap visualization that distinguishes occurrence coordinates from area reference coordinates.
* **Portuguese and English:** Language selector for the interface, curated descriptive data and Appendix S1 downloads.
* **Appendix S1:** 1,183 records grouped into 523 accepted taxa (falling back to the recorded name when no accepted name is supplied), with nine curated use categories.
* **Search & Filtering:** Query system by scientific name, common name, or bioeconomic utility.
* **Traceable Records:** Each taxon record lists its occurrence IDs, sources, dates, coordinates, uncertainty and georeferencing notes.
* **Data Export:** Download the original Appendix S1 workbook in the selected language, preserving all tabs and metadata.

## Installation

### Prerequisites
* Python 3.10 or higher
* Git

### Setup

1.  Clone the repository:
    ```bash
    git clone [https://github.com/anaalusouto/Munguba-Plataform.git](https://github.com/anaalusouto/Munguba-Plataform.git)
    cd Munguba-Plataform
    ```

2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    
    # Windows:
    venv\Scripts\activate
    
    # Linux/macOS:
    source venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To start the local development server, execute the following command:

```bash
python main.py
```
The application will be accessible at http://localhost:5000.

The public application reads `dados/Appendix_S1_Occurrence_records_PT.xlsx` and `dados/Appendix_S1_Occurrence_records_EN.xlsx` directly. Both files must be included in deployments. A MySQL database and Google service-account credentials are not required to browse or download the occurrence data. Photo metadata is read from the bundled workbook, with local and placeholder images as fallback.

The `Occurrences` tab provides the records. `dynamicProperties` supplies the curated use and plant-part vocabularies, and `Vocabularies` defines the Portuguese/English terms. Scientific names, vernacular names and source citations remain as recorded by the authors. Reading does not rewrite either workbook. Restart the application after replacing both files with a new matching version.

Of the 1,183 records, 260 have `georeferenceLevel=occurrence` and 923 have `georeferenceLevel=area`. The map shows the occurrence points and a separate, initially visible layer for uncertain reference locations. `/referencias-mapa` loads the area data independently. The 923 area records for 424 taxa share the APA Ilha do Combu footprint, so they are grouped into one searchable area rather than stacked at the same coordinate. The source's EPSG:4326 polygon and 3,416 m uncertainty radius are rendered beneath occurrence points. The layer follows category filters, can be hidden, and links each taxon to its record sheet. It describes an approximate reference area, not the exact position of a plant; no estimated individual points are generated. Leaflet 1.9.4 and its BSD license are bundled under `static/vendor/leaflet/` to avoid a dependency on the library CDN. Background tiles still come from OpenStreetMap.

Photos come from `dados/Fotos faltantes - Catálogo Munguba.xlsx`, read without modifying the workbook. Include this file in deployments. It is cached for one hour; restart the application to apply a replacement immediately. Original image URLs remain in the metadata; the bundled local WebP versions described below are used when available. Only when the workbook is absent does the application use the public Google photo sheet, tab `1140076266`, configurable with `FOTOS_PLANILHA_ID` and `FOTOS_PLANILHA_GID`. Matching tries accepted and original recorded names, including binomials without authorship. Valid medium-resolution images are used when high-resolution links are missing or raw Deep Zoom files; FSI raster image endpoints are supported. Sheet photos keep their author, license and source; local images and the placeholder are fallbacks. Failed reads are retried after one minute.

Additional GBIF photos and their attribution are stored in `dados/fotos_complementares.json`. Pre-generated WebP images live in `static/fotos/catalogo/`; `dados/fotos_miniaturas.json` maps existing photo URLs to local versions. Include both manifests and the image directory in deployments. Local images are preferred when available; original URLs are retained for provenance. No image downloads or searches run during a visitor request. The import rejects genus-only/fuzzy matches, requires a compatible plant family and an explicit reusable image license, and records the GBIF occurrence source. Taxa identified only to genus or `sp.` keep the placeholder.

To search remaining taxa, retry inaccessible links, and optimize existing images, install `requirements-dev.txt` and run `python scripts/buscar_fotos.py --existentes --reparar-links`. The original workbook remains unchanged. See `artifacts/busca-fotos.json` for search results and unresolved cases.

The catalogue builds 24 cards when opened, adds further batches on request, and searches all 523 taxa using a normalized in-memory index. Search input is debounced by 120 ms. Detailed records load on demand and the most recent 20 are retained in the page. The map creates only the 260 occurrence-level markers, using Canvas.

Tailwind styles and Remix Icon are served locally to avoid CDN failures and client-side CSS compilation. After changing utility classes in templates, rebuild `static/tailwind.css` with `npm exec --yes --package=tailwindcss@3.4.17 -- tailwindcss -c tailwind.config.cjs -i static/tailwind-input.css -o static/tailwind.css --minify`. Icon assets retain their Apache 2.0 license in `static/vendor/remixicon/LICENSE`.

The legacy `models.py` and `importar_excel.py` remain available for the previous MySQL workflow. They are not used by the public application; the old importer's `drop_all()` operation must not be used to load Appendix S1.

Run the regression checks with:

```bash
python -m unittest discover -s tests -v
```

The checks use the bundled Appendix files, without connecting to MySQL or the photo service. They cover record reconciliation, PT/EN content, language persistence, coordinates and original-file downloads. Detailed taxon sheets load on demand to keep the home response below the hosting body-size limit.

## Authors

* **Ana Luiza Souto** - *Lead Developer & Software Engineer*
  <br>Responsible for the full-stack implementation, architecture, and engineering of the platform.

* **MSc. Alcina Girotto** - *Lead Researcher & Co-Author*
  <br>Author of the Master's Thesis for which this software was developed as a technological product. Responsible for conceptualization, data curation, and scientific validation.

* **Dr. Marcos Paulo** - *Advisor & Project Coordinator*
  <br>Research advisor for both authors and co-author of the Munguba concept.

## Acknowledgments

The development of this project was supported by the **Amazon Foundation for Studies and Research (FAPESPA)** through a Technological Initiation Scholarship.

We gratefully acknowledge the **Museu Paraense Emílio Goeldi (MPEG)** for providing the necessary infrastructure, data, and scientific support throughout the research.

We also thank the **Centro Universitário do Estado do Pará (CESUPA)** for the institutional support provided to the **Bachelor of Computer Science degree**.
