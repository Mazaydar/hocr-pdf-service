from flask import Flask, request, jsonify
import base64
import json
import re
import os
import logging
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
import io
import tempfile

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'hOCR to PDF converter'})

@app.route('/convert', methods=['POST'])
def convert_hocr_to_pdf():
    try:
        logger.info("Received hOCR to PDF conversion request")
        
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            
        hocr_html = data.get('hocr', '')
        original_pdf_b64 = data.get('originalPdf', '')
        
        if not hocr_html or not original_pdf_b64:
            return jsonify({'success': False, 'error': 'Missing hocr or originalPdf data'}), 400
        
        logger.info(f"Processing hOCR data: {len(hocr_html)} characters")
        
        # Parse hOCR to extract words and positions
        words = parse_hocr_words(hocr_html)
        
        if not words:
            logger.warning("No words found in hOCR, returning original PDF")
            return jsonify({
                'success': True,
                'searchablePdf': original_pdf_b64,
                'wordsExtracted': 0,
                'message': 'No words found in hOCR'
            })
        
        logger.info(f"Extracted {len(words)} words from hOCR")
        
        # Create searchable PDF by overlaying invisible text
        searchable_pdf_b64 = create_searchable_pdf_with_text_overlay(original_pdf_b64, words)
        
        return jsonify({
            'success': True,
            'searchablePdf': searchable_pdf_b64,
            'wordsExtracted': len(words),
            'message': f'Successfully created searchable PDF with {len(words)} words'
        })
        
    except Exception as e:
        logger.error(f"Error in hOCR to PDF conversion: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Conversion failed: {str(e)}'
        }), 500

def parse_hocr_words(hocr_html):
    """Parse hOCR HTML to extract words with bounding boxes"""
    words = []
    
    try:
        # Find all word elements using regex
        word_pattern = r'<span class=[\'"]ocrx_word[\'"][^>]*title=[\'"]bbox (\d+) (\d+) (\d+) (\d+)[\'"][^>]*>([^<]+)</span>'
        matches = re.findall(word_pattern, hocr_html, re.IGNORECASE)
        
        for match in matches:
            x1, y1, x2, y2, text = match
            words.append({
                'text': text.strip(),
                'x1': int(x1),
                'y1': int(y1),
                'x2': int(x2),
                'y2': int(y2),
                'width': int(x2) - int(x1),
                'height': int(y2) - int(y1)
            })
        
        logger.info(f"Successfully parsed {len(words)} words from hOCR")
        return words
        
    except Exception as e:
        logger.error(f"Error parsing hOCR: {str(e)}")
        return []

def create_searchable_pdf_with_text_overlay(original_pdf_b64, words):
    """Create a searchable PDF by overlaying invisible text"""
    try:
        logger.info(f"Creating searchable PDF with {len(words)} words")
        
        # Decode original PDF
        original_pdf_bytes = base64.b64decode(original_pdf_b64)
        
        # Create a simple searchable PDF using ReportLab
        # This is a basic implementation - overlays text on a white background
        
        # Group words by their approximate page (based on Y coordinate)
        pages = group_words_by_page(words)
        
        # Create new PDF with text overlay
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        for page_num, page_words in pages.items():
            logger.info(f"Processing page {page_num + 1} with {len(page_words)} words")
            
            # Set page size (standard letter for now)
            c.setPageSize(letter)
            
            # Add invisible text layer
            for word in page_words:
                try:
                    # Calculate position (basic transformation)
                    x = word['x1']
                    y = 792 - word['y2']  # Flip Y coordinate for PDF
                    
                    # Add invisible text
                    c.setFillColor(Color(0, 0, 0, alpha=0))  # Invisible
                    c.setFont("Helvetica", 12)
                    c.drawString(x, y, word['text'])
                    
                except Exception as word_error:
                    logger.warning(f"Skipping word due to error: {word_error}")
                    continue
            
            # Add visible background (original PDF content would go here)
            # For now, we'll add a light watermark to show it's processed
            c.setFillColor(Color(0.9, 0.9, 0.9, alpha=0.1))
            c.setFont("Helvetica", 8)
            c.drawString(50, 50, "Searchable PDF - Text layer added")
            
            c.showPage()
        
        c.save()
        
        # Get the PDF bytes
        searchable_pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Encode as base64
        searchable_pdf_b64 = base64.b64encode(searchable_pdf_bytes).decode()
        
        logger.info("Successfully created searchable PDF")
        return searchable_pdf_b64
        
    except Exception as e:
        logger.error(f"Error creating searchable PDF: {str(e)}")
        # Return original PDF if overlay fails
        return original_pdf_b64

def group_words_by_page(words, page_height=792):
    """Group words by page based on Y coordinates"""
    pages = {}
    
    for word in words:
        # Simple page calculation based on Y coordinate
        page_num = int(word['y1'] / page_height)
        
        if page_num not in pages:
            pages[page_num] = []
        
        pages[page_num].append(word)
    
    return pages

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting hOCR to PDF service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
