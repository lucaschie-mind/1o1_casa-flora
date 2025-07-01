
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = None
async_session = None

Base = declarative_base()

if DATABASE_URL and DATABASE_URL.startswith("postgresql+asyncpg"):
    try:
        engine = create_async_engine(DATABASE_URL, echo=True)
        async_session = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    except Exception as e:
        print(f"Erro ao criar async engine: {e}")

class Registro1o1(Base):
    __tablename__ = "registros_1o1"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome_teams = Column(Text)
    email_employee = Column(Text)
    id_full = Column(Integer)
    nome_gestor = Column(Text)
    email_gestor = Column(Text)
    data_1o1 = Column(Date)
    abertura = Column(Text)
    abertura_comentario = Column(Text)
    conquistas = Column(Text)
    principais_assuntos = Column(Text)
    combinados = Column(Text)
    datastamp = Column(DateTime)
    relatorio = Column(Text, nullable=True)
