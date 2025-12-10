"""
Script simples para carregar documentos no Qdrant.
Uso: python upload_docs.py [pasta_com_pdfs]
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib

# Carregar .env
load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = int(os.getenv("QDRANT_PORT"))
COLLECTION_NAME = "technical_solutions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_embedding(text: str, client: OpenAI) -> list:
    """Gera embedding usando OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list:
    """Divide texto em chunks."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - chunk_overlap
    
    return chunks


def upload_pdf(pdf_path: str, qdrant_client: QdrantClient, openai_client: OpenAI):
    """Carrega um único PDF no Qdrant."""
    print(f"\n📄 A processar: {Path(pdf_path).name}")
    
    try:
        # 1. Carregar PDF
        reader = PdfReader(pdf_path)
        print(f"   ✓ {len(reader.pages)} páginas carregadas")
        
        # 2. Extrair texto e dividir em chunks
        all_chunks = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            chunks = split_text(text, chunk_size=1000, chunk_overlap=200)
            
            for chunk in chunks:
                if chunk.strip():
                    all_chunks.append({
                        "text": chunk,
                        "metadata": {
                            "source_file": Path(pdf_path).name,
                            "page": page_num + 1
                        }
                    })
        
        print(f"   ✓ {len(all_chunks)} chunks criados")
        
        # 3. Criar embeddings e adicionar ao Qdrant
        points = []
        for i, chunk_data in enumerate(all_chunks):
            # Gerar embedding
            embedding = get_embedding(chunk_data["text"], openai_client)
            
            # Criar ID único
            doc_id = int(hashlib.md5(chunk_data["text"].encode()).hexdigest()[:8], 16)
            
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload=chunk_data
            )
            points.append(point)
            
            if (i + 1) % 10 == 0:
                print(f"   Processados {i + 1}/{len(all_chunks)} chunks...")
        
        # Upload para Qdrant
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
        print(f"   ✅ {len(points)} chunks carregados no Qdrant!")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False


def main():
    print("=" * 60)
    print("  FRANKENSTEIN - Upload Simples de Documentos")
    print("=" * 60)
    
    # Verificar API Key
    if not OPENAI_API_KEY:
        print("\n❌ ERRO: OPENAI_API_KEY não configurada no .env")
        sys.exit(1)
    
    # Determinar pasta
    if len(sys.argv) > 1:
        folder = Path(sys.argv[1])
    else:
        folder = Path(__file__).parent / "knowledge_base"
    
    if not folder.exists():
        print(f"\n❌ Pasta não encontrada: {folder}")
        print(f"💡 Criando pasta: {folder}")
        folder.mkdir(parents=True, exist_ok=True)
    
    # Encontrar PDFs
    pdfs = list(folder.glob("*.pdf"))
    
    if not pdfs:
        print(f"\n⚠️  Nenhum PDF encontrado em: {folder}")
        print("\n💡 Coloque seus PDFs na pasta 'knowledge_base/' e execute novamente.")
        sys.exit(0)
    
    print(f"\n📁 Pasta: {folder}")
    print(f"📊 Encontrados: {len(pdfs)} PDF(s)\n")
    
    # Listar PDFs
    for i, pdf in enumerate(pdfs, 1):
        print(f"  {i}. {pdf.name}")
    
    # Confirmar
    print("\n" + "-" * 60)
    resposta = input("Carregar todos os PDFs? (s/n): ").lower().strip()
    
    if resposta != 's':
        print("❌ Cancelado pelo utilizador.")
        sys.exit(0)
    
    print("\n🚀 Iniciando upload...\n")
    
    # Conectar ao Qdrant
    try:
        qdrant_url = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
        qdrant_client = QdrantClient(url=qdrant_url)
        qdrant_client.get_collections()
        print(f"✅ Conectado ao Qdrant em {qdrant_url}")
    except Exception as e:
        print(f"❌ Erro ao conectar ao Qdrant: {e}")
        print(f"💡 Verifica se o Docker está a correr: docker-compose up -d")
        sys.exit(1)
    
    # Criar coleção se não existir
    collections = [col.name for col in qdrant_client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        print(f"📦 Criando coleção '{COLLECTION_NAME}'...")
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
    
    # Inicializar OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Processar cada PDF
    sucesso = 0
    falhas = 0
    
    for pdf in pdfs:
        if upload_pdf(str(pdf), qdrant_client, openai_client):
            sucesso += 1
        else:
            falhas += 1
    
    # Resumo
    print("\n" + "=" * 60)
    print("  RESUMO")
    print("=" * 60)
    print(f"✅ Sucesso: {sucesso}")
    print(f"❌ Falhas: {falhas}")
    
    # Info da coleção
    info = qdrant_client.get_collection(COLLECTION_NAME)
    print(f"📊 Total de vetores: {info.points_count}")
    print(f"🔗 Dashboard: http://{QDRANT_HOST}:{QDRANT_PORT}/dashboard")
    print("=" * 60)


if __name__ == "__main__":
    main()
