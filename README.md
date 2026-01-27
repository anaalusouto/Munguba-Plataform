# 🌿 Plataforma Munguba

> **Mapeamento da biodiversidade e potencial bioeconômico na Ilha do Combu.**
> Projeto de Iniciação Científica (PIBICTI) - Museu Paraense Emílio Goeldi (MPEG).

A **Plataforma Munguba** é uma aplicação web interativa desenvolvida para catalogar, georreferenciar e visualizar espécies vegetais com potencial econômico na região insular de Belém/PA. O sistema utiliza dados reais coletados em campo e armazenados em nuvem para gerar dashboards e mapas dinâmicos.

![Status do Projeto](https://img.shields.io/badge/Status-Concluído-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-Framework-lightgrey)

---

## 🚀 Funcionalidades

- **🗺️ Mapa Interativo:** Visualização espacial das coletas com pinos coloridos e pop-ups informativos (Leaflet.js).
- **📊 Dashboard de Dados:** Estatísticas em tempo real sobre total de espécies, famílias botânicas e categorias de uso.
- **🔍 Catálogo Inteligente:**
  - Busca textual (Nome popular, científico, família).
  - Filtros dinâmicos por **Categoria de Uso** (Medicinal, Alimentícia, etc.).
  - Filtros por **Parte da Planta** (Fruto, Folha, Casca, etc.).
- **📱 Design Responsivo:** Interface moderna e adaptável para celulares e computadores (TailwindCSS).
- **☁️ Integração Google Sheets:** Banco de dados conectado diretamente a uma planilha do Google para facilitar a atualização por biólogos.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python (Flask).
- **Banco de Dados:** Google Sheets API (`gspread`).
- **Frontend:** HTML5, CSS3, TailwindCSS (via CDN).
- **Mapas:** Leaflet.js + OpenStreetMap.
- **Ícones:** Remix Icon.

---

