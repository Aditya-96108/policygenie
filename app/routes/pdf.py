import logging
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os

router = APIRouter()
logger = logging.getLogger(__name__)

class PdfRequest(BaseModel):
    text: str
    filename: str = "report.pdf"

@router.post("/download-pdf")
async def download_pdf_endpoint(request: PdfRequest):
    try:
        processed_dir = "data/processed"
        os.makedirs(processed_dir, exist_ok=True)
        pdf_path = f"{processed_dir}/{request.filename}"
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        for line in request.text.split("\n"):
            if line.strip():
                elements.append(Paragraph(line, styles['Normal']))
                elements.append(Spacer(1, 12))
        
        doc.build(elements)
        
        with open(pdf_path, "rb") as f:
            pdf_content = f.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={request.filename}"}
        )
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise HTTPException(500, str(e))
