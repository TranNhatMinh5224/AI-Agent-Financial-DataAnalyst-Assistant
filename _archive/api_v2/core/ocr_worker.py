import fitz  # PyMuPDF
from paddleocr import PaddleOCR
import numpy as np
import cv2
import io
import uuid

from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

from .. import models
from .storage import minio_client
from ..config.config import settings

# Initialize PaddleOCR globally so it stays loaded in memory
# Setting use_angle_cls=True, lang="en" (Vietnamese or English as needed)
# PaddleOCR defaults to downloading models on first run
try:
    ocr_engine = PaddleOCR(use_angle_cls=True, lang="en") # Dùng tiếng Anh hoặc tiếng Việt ('vi')
except Exception as e:
    ocr_engine = None
    print(f"Lỗi khởi tạo PaddleOCR: {e}")

# Initialize Embedding Model & Qdrant Client
try:
    embed_model = SentenceTransformer("BAAI/bge-m3")
except:
    embed_model = None

qdrant = QdrantClient(url=settings.QDRANT_URL)
COLLECTION_NAME = "vifinqa_documents"

try:
    qdrant.get_collection(COLLECTION_NAME)
except:
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )

def chunk_text(text: str, chunk_size: int = 1000) -> list:
    """Chia nhỏ văn bản thành các đoạn (chunks)"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks

def convert_pdf_to_images(pdf_bytes: bytes) -> list:
    """
    Sử dụng PyMuPDF để chuyển PDF (bytes) thành mảng numpy ảnh.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        # Tăng phân giải (zoom) để OCR đọc rõ hơn
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        
        # Chuyển fitz pixmap sang numpy array (RGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        images.append(img)
    return images

def process_document_with_paddleocr(workspace_id: str, document_id: str, object_name: str, db: Session):
    """
    Background Task thực thi:
    1. Lấy file từ MinIO.
    2. Chạy PaddleOCR lấy text.
    3. Đẩy qua Pipeline làm sạch & nhúng.
    4. Lưu vào Qdrant & Cập nhật PostgreSQL.
    """
    try:
        # Cập nhật trạng thái "processing"
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if doc:
            doc.status = "processing"
            db.commit()

        # 1. Download file từ MinIO
        file_bytes = minio_client.download_file_bytes(object_name)
        
        images = []
        if object_name.lower().endswith(".pdf"):
            images = convert_pdf_to_images(file_bytes)
        else:
            # Xử lý ảnh trực tiếp
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            images.append(img)
        
        # 2. Chạy PaddleOCR
        full_text = ""
        for idx, img in enumerate(images):
            if ocr_engine:
                result = ocr_engine.ocr(img, cls=True)
                page_text = []
                for res in result:
                    if res:
                        for line in res:
                            text = line[1][0]
                            page_text.append(text)
                
                full_text += f"\n===== PAGE {idx+1} =====\n"
                full_text += "\n".join(page_text)
                full_text += "\n"
        
        # 3. Chạy Pipeline Làm sạch & Embeddings
        if embed_model and full_text.strip():
            chunks = chunk_text(full_text)
            embeddings = embed_model.encode(chunks)
            
            points = []
            for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector.tolist(),
                        payload={
                            "workspace_id": workspace_id,
                            "document_id": document_id,
                            "text": chunk,
                            "page_index": i # Approximate
                        }
                    )
                )
            
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
        
        # 4. Đánh dấu hoàn tất
        if doc:
            doc.status = "ready"
            db.commit()
            
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        doc = db.query(models.Document).filter(models.Document.id == document_id).first()
        if doc:
            doc.status = "error"
            db.commit()
