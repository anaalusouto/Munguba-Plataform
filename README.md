# 🌿 Plataforma Munguba

> **Sistema de Bioeconomia e Biodiversidade da APA Ilha do Combu**

O **Munguba** é uma aplicação web desenvolvida para catalogar, visualizar e padronizar dados sobre espécies florísticas de valor bioeconômico na Amazônia. O projeto conecta tecnologia e ciência aberta, promovendo a valorização da flora local através de visualizações geoespaciais e interoperabilidade de dados.

---

## 🎯 Objetivo

O projeto visa aplicar os **Princípios FAIR** (Findable, Accessible, Interoperable, Reusable) em dados de ocorrência de espécies. A plataforma permite que pesquisadores e a comunidade visualizem a distribuição das espécies na Ilha do Combu e acessem dados padronizados no formato internacional **Darwin Core (DwC)**.

---

## 🚀 Funcionalidades

- **Mapeamento Interativo:** Visualização geoespacial das espécies utilizando **Leaflet.js**.
- **Busca & Filtragem:** Pesquisa rápida por nome científico, popular ou uso bioeconômico.
- **Processamento ETL:** Rotinas automatizadas (`darwin_core.py`) que cruzam dados de campo com bases taxonômicas de referência (GBIF).
- **Exportação de Dados:** Download de datasets validados e prontos para uso científico.
- **Alta Performance:** Sistema de cache em memória para acesso instantâneo aos dados.

---

## 🛠️ Arquitetura e Tecnologias

O sistema segue o padrão arquitetural **MVC (Model-View-Controller)** adaptado para web.

| Camada | Tecnologia | Função |
| :--- | :--- | :--- |
| **Front-end (View)** | HTML5, Tailwind CSS, Jinja2 | Renderização responsiva e mapas interativos. |
| **Back-end (Controller)** | Python (Flask) | Orquestração de rotas e APIs RESTful (`main.py`). |
| **Data Engineering (Model)** | Pandas, Darwin Core Logic | ETL, limpeza de dados e validação (`darwin_core.py`). |
| **Persistência** | Google Sheets API + Cache | Armazenamento híbrido e ágil. |
| **Deploy** | Vercel | Configuração Serverless (`vercel.json`). |

---

## 📂 Estrutura do Projeto

```text
📁 Plataforma-Munguba/
├── 📂 static/           # Arquivos estáticos (CSS, JS, Imagens)
├── 📂 templates/        # Templates HTML (Renderização Jinja2)
├── 📂 dados/            # Bases de referência taxonômica (Excel/CSV)
├── 📄 main.py           # Aplicação Principal (Controller Flask)
├── 📄 darwin_core.py    # Módulo de Lógica de Negócio e ETL
├── 📄 requirements.txt  # Dependências do projeto
├── 📄 vercel.json       # Configuração de Deploy (Vercel)
└── 📄 README.md         # Documentação
```

## 🤝 Contexto
Este projeto foi desenvolvido no âmbito institucional, como parte de uma iniciativa de Iniciação Tecnológica voltada para a Bioeconomia Amazônica e Ciência Aberta.
