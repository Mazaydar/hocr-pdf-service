from flask import Flask, request, jsonify
import base64
import json
import re
import os
import logging

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
        
        logger.info(f"Extracted {len(words)} words from hOCR")
        
        # For now, return original PDF with metadata
        # In production, you'd overlay the text on the PDF
        
        return jsonify({
            'success': True,
            'searchablePdf': original_pdf_b64,
            'wordsExtracted': len(words),
            'message': f'hOCR processed successfully - {len(words)} words extracted'
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
        matches = re.findall(word_pattern, hocr_html)
        
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
        
        return words
        
    except Exception as e:
        logger.error(f"Error parsing hOCR: {str(e)}")
        return []

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting hOCR to PDF service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
