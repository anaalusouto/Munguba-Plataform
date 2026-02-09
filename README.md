# Munguba Platform: Bioeconomy and Biodiversity System of the Combu Island APA

**Munguba** is a web-based application designed to catalog, visualize, and standardize data on floristic species with bioeconomic value in the Amazon. The project integrates technology and Open Science, promoting the valorization of local flora through geospatial visualizations and data interoperability based on the Darwin Core (DwC) standard.

## Overview

This project applies the **FAIR Principles** (Findable, Accessible, Interoperable, Reusable) to species occurrence data. The platform allows researchers and the community to visualize species distribution on Combu Island and access standardized data compliant with international biodiversity informatics standards.

## Features

* **Interactive Mapping:** Geospatial visualization of species distribution using Leaflet.js.
* **Search & Filtering:** Query system by scientific name, common name, or bioeconomic utility.
* **ETL Processing:** Automated Extract, Transform, and Load routines to cross-reference field data with taxonomic authorities (GBIF).
* **Data Export:** Generation of validated datasets ready for scientific analysis.

## Installation

### Prerequisites
* Python 3.8 or higher
* Git

### Setup

1.  Clone the repository:
    ```bash
    git clone [https://github.com/anaalusouto/Plataforma-Munguba.git](https://github.com/anaalusouto/Plataforma-Munguba.git)
    cd Plataforma-Munguba
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

Note: This application requires a valid credentials.json file in the root directory to authenticate with the Google Sheets API.

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

We also thank the **Centro Universitário do Estado do Pará (CESUPA)** for the institutional support provided to the Computer Science undergraduate program.
