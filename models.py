from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# Carrega o cofre (o arquivo .env)
load_dotenv()

app = Flask(__name__)

# Puxa a senha do cofre de forma segura!
senha_mysql = os.getenv("SENHA_MYSQL")

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://root:{quote_plus(senha_mysql)}@localhost:3306/munguba_db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Taxon(db.Model):
    __tablename__ = 'TAXON'
    id_taxon = db.Column(db.Integer, primary_key=True)
    scientificNameAccepted = db.Column(db.String(255), nullable=False)
    authorshipAccepted = db.Column(db.String(255))
    reino = db.Column(db.String(100))
    filo = db.Column(db.String(100))
    classe = db.Column(db.String(100))
    ordem = db.Column(db.String(100))
    familia = db.Column(db.String(100))
    genero = db.Column(db.String(100))
    especie = db.Column(db.String(100))
    taxonKey = db.Column(db.String(100))
    speciesKey = db.Column(db.String(100))

    sinonimos = db.relationship('Sinonimo', backref='taxon', lazy=True)
    ocorrencias = db.relationship('Occurrence', backref='taxon', lazy=True)
    bioeconomico = db.relationship('Bioeconomico', backref='taxon', uselist=False, lazy=True)

class Sinonimo(db.Model):
    __tablename__ = 'SINONIMO'
    id_sinonimo = db.Column(db.Integer, primary_key=True)
    id_taxon = db.Column(db.Integer, db.ForeignKey('TAXON.id_taxon'), nullable=False)
    scientificNameSynonym = db.Column(db.String(255), nullable=False)

class Bioeconomico(db.Model):
    __tablename__ = 'BIOECONOMICO'
    id_bioeconomico = db.Column(db.Integer, primary_key=True)
    id_taxon = db.Column(db.Integer, db.ForeignKey('TAXON.id_taxon'), unique=True, nullable=False)

    nome_popular = db.Column(db.Text)
    origem_habitat = db.Column(db.Text)
    potencial_bioeconomico = db.Column(db.Text)
    partes_planta = db.Column(db.Text)
    importancia = db.Column(db.Text)
    referencias_bibliograficas = db.Column(db.Text)

class Localizacao(db.Model):
    __tablename__ = 'LOCALIZACAO'
    id_localizacao = db.Column(db.Integer, primary_key=True)
    codigo_pais = db.Column(db.String(10))
    municipio = db.Column(db.String(150))
    estado_provincia = db.Column(db.String(150))
    ocorrencias = db.relationship('Occurrence', backref='localizacao_ref', lazy=True)

class Referencia(db.Model):
    __tablename__ = 'REFERENCIA'
    id_referencia = db.Column(db.Integer, primary_key=True)
    referencia = db.Column(db.Text)
    citacao_bibliografica = db.Column(db.Text)
    ocorrencias = db.relationship('Occurrence', backref='referencia_ref', lazy=True)

class Occurrence(db.Model):
    __tablename__ = 'OCCURRENCE'
    occurrenceID = db.Column(db.String(100), primary_key=True)
    id_taxon = db.Column(db.Integer, db.ForeignKey('TAXON.id_taxon'), nullable=False)
    id_localizacao = db.Column(db.Integer, db.ForeignKey('LOCALIZACAO.id_localizacao'))
    id_referencia = db.Column(db.Integer, db.ForeignKey('REFERENCIA.id_referencia'))

    scientificName = db.Column(db.String(255))
    kingdom = db.Column(db.String(100))
    phylum = db.Column(db.String(100))
    class_ = db.Column('class', db.String(100))
    order = db.Column(db.String(100))
    family = db.Column(db.String(100))
    genus = db.Column(db.String(100))
    species = db.Column(db.String(100))
    gbifId = db.Column(db.String(100))
    basisOfRecord = db.Column(db.String(100))
    decimalLatitude = db.Column(db.Float)
    decimalLongitude = db.Column(db.Float)
    eventDate = db.Column(db.String(50))
    iucnRedListCategory = db.Column(db.String(50))
    reference = db.Column(db.Text)
    bibliographicCitation = db.Column(db.Text)
    countryCode = db.Column(db.String(10))
    municipality = db.Column(db.String(150))
    stateProvince = db.Column(db.String(150))

with app.app_context():
    db.create_all()
    print("Banco de dados da dissertação atualizado com sucesso!")