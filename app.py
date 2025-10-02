"""
AI-powered Daily Worker Search Database
Copyright (c) 2025 Benjamin Goldstein
Licensed under the MIT License - see LICENSE file for details

Streamlit application for searching historical Daily Worker newspapers.
"""

import streamlit as st
from datetime import date, timedelta
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from vector_database_hosted import VectorDatabaseHosted
from models import SearchQuery, SearchResult, NewspaperMetadata, DocumentChunk
from config import config
from loguru import logger
from response_generator import ResponseGenerator
import re
from io import BytesIO
from datetime import datetime
import base64
from auth import AuthManager
from usage_monitor import UsageMonitor
import requests
import gdown

# Try to import PDF generation libraries
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Historical Newspaper Search",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    
    .search-result {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .result-header {
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
    }
    
    .result-citation {
        color: #6c757d;
        font-style: italic;
        margin-bottom: 0.5rem;
    }
    
    .result-content {
        color: #212529;
        line-height: 1.6;
    }
    
    .relevance-score {
        background-color: #e9ecef;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.875rem;
        color: #495057;
    }
    
    .filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def make_source_references_clickable_for_pdf(ai_response: str, search_results: List[SearchResult]) -> str:
    """Convert [Source N] references in AI responses to clickable links for PDFs."""
    if not ai_response or not search_results:
        return ai_response
    
    import re
    
    def replace_source_ref(match):
        source_num = int(match.group(1))
        # Source numbers are 1-indexed, list is 0-indexed
        if 1 <= source_num <= len(search_results):
            result = search_results[source_num - 1]
            
            # Get the Internet Archive URL
            source_url = result.chunk.newspaper_metadata.source_url
            if not source_url:
                source_url = reconstruct_internet_archive_url(result)
            
            if source_url:
                # Create clickable link for PDF using reportlab link format
                return f'<link href="{source_url}">[Source {source_num}]</link>'
        
        # Return original if no URL found
        return match.group(0)
    
    # Find and replace all [Source N] references
    pattern = r'\[Source (\d+)\]'
    result = re.sub(pattern, replace_source_ref, ai_response)
    
    return result


def make_source_references_clickable_for_pdf(text: str, search_results: List[SearchResult]) -> str:
    """Replace [Source N] with clickable links in PDF format."""
    import re
    
    def replace_source(match):
        source_num = int(match.group(1))
        if 1 <= source_num <= len(search_results):
            result = search_results[source_num - 1]
            # Get the Internet Archive URL
            source_url = result.chunk.newspaper_metadata.source_url
            if not source_url:
                source_url = reconstruct_internet_archive_url(result)
            
            if source_url:
                # Return a clickable link for PDF
                return f'<link href="{source_url}" color="blue">[Source {source_num}]</link>'
        return match.group(0)
    
    # Replace [Source N] with clickable links
    return re.sub(r'\[Source (\d+)\]', replace_source, text)


def parse_ai_response_for_pdf(ai_response: str, styles, search_results: List[SearchResult] = None):
    """Parse AI response and convert to properly formatted PDF elements."""
    elements = []
    
    # Make source references clickable if search results are provided
    if search_results:
        ai_response = make_source_references_clickable_for_pdf(ai_response, search_results)
    
    # Create custom styles for AI content
    ai_heading_style = ParagraphStyle(
        'AIHeading',
        parent=styles['Heading3'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=10,
        textColor=colors.HexColor('#1a472a')
    )
    
    ai_subheading_style = ParagraphStyle(
        'AISubheading',
        parent=styles['Heading4'],
        fontSize=10,
        spaceAfter=6,
        spaceBefore=8,
        textColor=colors.HexColor('#2a5298'),
        fontName='Helvetica-Bold'
    )
    
    ai_normal_style = ParagraphStyle(
        'AINormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        leftIndent=0,
        bulletIndent=20
    )
    
    ai_bullet_style = ParagraphStyle(
        'AIBullet',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=20,
        bulletIndent=20,
        bulletFontName='Helvetica',
        bulletText='•'
    )
    
    # Split response into lines and process
    lines = ai_response.split('\n')
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        
        if not line:
            # Empty line - end current paragraph and add space
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            elements.append(Spacer(1, 6))
            continue
        
        # Check for different types of formatting
        if line.startswith('##') and not line.startswith('###'):
            # Main heading (## heading)
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            
            heading_text = line.replace('##', '').strip()
            # Clean HTML entities and tags
            import html
            import re
            heading_text = html.unescape(heading_text)
            # Preserve <link> tags but remove other HTML tags
            heading_text = re.sub(r'<(?!/?link)[^>]+>', '', heading_text)
            # Don't remove < > from link tags
            heading_text = re.sub(r'&(?!(?:lt|gt|amp);)', '', heading_text)
            elements.append(Paragraph(heading_text, ai_heading_style))
            
        elif line.startswith('###'):
            # Sub heading (### heading)
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            
            subheading_text = line.replace('###', '').strip()
            # Clean HTML entities and tags
            import html
            import re
            subheading_text = html.unescape(subheading_text)
            # Preserve <link> tags but remove other HTML tags
            subheading_text = re.sub(r'<(?!/?link)[^>]+>', '', subheading_text)
            # Don't remove < > from link tags
            subheading_text = re.sub(r'&(?!(?:lt|gt|amp);)', '', subheading_text)
            elements.append(Paragraph(subheading_text, ai_subheading_style))
            
        elif line.startswith('**') and line.endswith('**') and len(line) > 4:
            # Bold heading line
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            
            bold_text = line.replace('**', '').strip()
            # Clean HTML entities and tags
            import html
            import re
            bold_text = html.unescape(bold_text)
            # Preserve <link> tags but remove other HTML tags
            bold_text = re.sub(r'<(?!/?link)[^>]+>', '', bold_text)
            # Don't remove < > from link tags
            bold_text = re.sub(r'&(?!(?:lt|gt|amp);)', '', bold_text)
            elements.append(Paragraph(f"<b>{bold_text}</b>", ai_subheading_style))
            
        elif line.startswith('- ') or line.startswith('• '):
            # Bullet point
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            
            bullet_text = line.replace('- ', '').replace('• ', '').strip()
            # Clean up any remaining markdown and HTML
            import html
            import re
            bullet_text = bullet_text.replace('**', '')
            bullet_text = html.unescape(bullet_text)
            # Preserve <link> tags but remove other HTML tags
            bullet_text = re.sub(r'<(?!/?link)[^>]+>', '', bullet_text)
            # Don't remove < > from link tags
            bullet_text = re.sub(r'&(?!(?:lt|gt|amp);)', '', bullet_text)
            elements.append(Paragraph(f"• {bullet_text}", ai_bullet_style))
            
        elif line.startswith('*') and not line.startswith('**'):
            # Single asterisk bullet
            if current_paragraph:
                text = ' '.join(current_paragraph)
                elements.append(Paragraph(text, ai_normal_style))
                current_paragraph = []
            
            bullet_text = line.replace('*', '').strip()
            # Clean HTML entities and tags
            import html
            import re
            bullet_text = html.unescape(bullet_text)
            # Preserve <link> tags but remove other HTML tags
            bullet_text = re.sub(r'<(?!/?link)[^>]+>', '', bullet_text)
            # Don't remove < > from link tags
            bullet_text = re.sub(r'&(?!(?:lt|gt|amp);)', '', bullet_text)
            elements.append(Paragraph(f"• {bullet_text}", ai_bullet_style))
            
        else:
            # Regular text - accumulate into paragraph
            # Clean up markdown formatting and HTML
            import html
            import re
            clean_line = line.replace('**', '').replace('*', '')
            # Clean HTML entities and tags
            clean_line = html.unescape(clean_line)
            # Preserve <link> tags but remove other HTML tags
            clean_line = re.sub(r'<(?!/?link)[^>]+>', '', clean_line)
            # Don't remove < > from link tags
            clean_line = re.sub(r'&(?!(?:lt|gt|amp);)', '', clean_line)
            current_paragraph.append(clean_line)
    
    # Add any remaining paragraph
    if current_paragraph:
        text = ' '.join(current_paragraph)
        elements.append(Paragraph(text, ai_normal_style))
    
    return elements


def generate_full_conversation_pdf() -> BytesIO:
    """Generate PDF for the entire conversation history."""
    if not PDF_AVAILABLE:
        raise ImportError("PDF generation not available. Install reportlab: pip install reportlab")
    
    if not st.session_state.conversation_history:
        raise ValueError("No conversation history available")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#2a5298')
    )
    
    exchange_title_style = ParagraphStyle(
        'ExchangeTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=15,
        spaceBefore=10,
        textColor=colors.HexColor('#1a472a'),
        borderWidth=1,
        borderColor=colors.HexColor('#2a5298'),
        borderPadding=5,
        backColor=colors.HexColor('#f8f9fa')
    )
    
    # Build PDF content
    content = []
    
    # Title page
    content.append(Paragraph("Complete Conversation History", title_style))
    content.append(Paragraph("Historical Newspaper Search", styles['Heading3']))
    content.append(Spacer(1, 30))
    
    # Summary information
    content.append(Paragraph("Conversation Summary", heading_style))
    summary_info = [
        ["Total Exchanges:", str(len(st.session_state.conversation_history))],
        ["Date Range:", f"{st.session_state.conversation_history[0]['timestamp'].strftime('%Y-%m-%d')} to {st.session_state.conversation_history[-1]['timestamp'].strftime('%Y-%m-%d')}"],
        ["Total Sources Used:", str(len(st.session_state.used_sources))],
        ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]
    
    summary_table = Table(summary_info, colWidths=[2.5*inch, 3.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 30))
    
    # Add page break before exchanges
    from reportlab.platypus import PageBreak
    content.append(PageBreak())
    
    # Process each exchange
    for i, exchange in enumerate(st.session_state.conversation_history):
        exchange_num = i + 1
        
        # Exchange header
        content.append(Paragraph(f"Exchange {exchange_num}", exchange_title_style))
        
        # Exchange details
        search_type = "Unknown"
        if exchange.get('search_query'):
            search_type = exchange['search_query'].search_type.title()
        
        exchange_info = [
            ["Query:", exchange['query']],
            ["Timestamp:", exchange['timestamp'].strftime("%Y-%m-%d %H:%M:%S")],
            ["Search Type:", search_type],
            ["Sources Used:", str(len(exchange.get('source_ids', [])))]
        ]
        
        exchange_table = Table(exchange_info, colWidths=[2*inch, 4*inch])
        exchange_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f8ff')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        content.append(exchange_table)
        content.append(Spacer(1, 15))
        
        # AI Response or Source Analysis
        response_mode = exchange.get('response_mode', 'Essay Generation')
        
        if response_mode == "Source Analysis" and exchange.get('source_analyses'):
            content.append(Paragraph("Source Analysis", heading_style))
            
            # Add each source analysis
            for j, analysis_data in enumerate(exchange['source_analyses'], 1):
                result = analysis_data.get('result')
                analysis = analysis_data.get('analysis')
                
                if not result or not analysis:
                    continue
                    
                # Source header - escape any HTML in the text
                import html
                newspaper_name = html.escape(result.chunk.newspaper_metadata.newspaper_name)
                citation = html.escape(result.format_citation())
                header_text = f"Source {j}: {newspaper_name} - {citation}"
                try:
                    content.append(Paragraph(header_text, styles['Heading4']))
                except Exception as e:
                    # Fallback if there's still an issue
                    logger.error(f"Error adding header paragraph: {e}")
                    content.append(Paragraph(f"Source {j}", styles['Heading4']))
                
                # Add Internet Archive link if available
                source_url = result.chunk.newspaper_metadata.source_url
                if not source_url:
                    source_url = reconstruct_internet_archive_url(result)
                if source_url:
                    try:
                        # Escape URL for safety
                        safe_url = html.escape(source_url, quote=False)  # Don't escape quotes in URLs
                        content.append(Paragraph(f"<b>Source URL:</b> <link href='{safe_url}'>{safe_url}</link>", styles['Normal']))
                        content.append(Spacer(1, 6))
                    except Exception as e:
                        logger.error(f"Error adding URL paragraph: {e}")
                        # Try without link formatting
                        try:
                            content.append(Paragraph(f"<b>Source URL:</b> {source_url}", styles['Normal']))
                            content.append(Spacer(1, 6))
                        except:
                            pass
                
                # Parse and format the analysis using the same function as single exchange PDF
                try:
                    formatted_analysis = parse_ai_response_for_pdf(analysis, styles)
                    for element in formatted_analysis:
                        content.append(element)
                except Exception as e:
                    logger.error(f"Error formatting analysis for source {j}: {e}")
                    # Fallback - add raw text without formatting
                    try:
                        # Remove any HTML tags and add as plain text
                        import re
                        clean_analysis = re.sub(r'<[^>]+>', '', analysis)
                        clean_analysis = html.unescape(clean_analysis)
                        content.append(Paragraph(clean_analysis[:1000] + "...", styles['Normal']))
                    except:
                        content.append(Paragraph("Error displaying analysis", styles['Normal']))
                
                content.append(Spacer(1, 15))
            
            content.append(Spacer(1, 20))
            
        elif exchange.get('response'):
            content.append(Paragraph("AI Response", heading_style))
            
            # Parse and format AI response
            formatted_ai_content = parse_ai_response_for_pdf(exchange['response'], styles, exchange.get('sources', []))
            for element in formatted_ai_content:
                content.append(element)
            
            content.append(Spacer(1, 20))
        
        # Sources section
        if exchange.get('sources'):
            content.append(Paragraph("Sources Referenced", heading_style))
            content.append(Paragraph(f"This exchange referenced {len(exchange['sources'])} sources:", styles['Normal']))
            content.append(Spacer(1, 10))
            
            # Show detailed source information
            for j, result in enumerate(exchange['sources'], 1):
                try:
                    # Source header - escape HTML
                    import html
                    newspaper_name = html.escape(result.chunk.newspaper_metadata.newspaper_name)
                    source_header = f"Source {j}: {newspaper_name} " \
                                   f"(Relevance: {int(result.relevance_score * 100)}%)"
                    content.append(Paragraph(source_header, styles['Heading4']))
                    
                    # Citation - escape HTML
                    citation = html.escape(result.format_citation())
                    content.append(Paragraph(f"<b>Citation:</b> {citation}", styles['Normal']))
                    
                    # Internet Archive link
                    source_url = result.chunk.newspaper_metadata.source_url
                    if not source_url:
                        source_url = reconstruct_internet_archive_url(result)
                    if source_url:
                        try:
                            safe_url = html.escape(source_url, quote=False)
                            content.append(Paragraph(f"<b>Source URL:</b> <link href='{safe_url}'>{safe_url}</link>", styles['Normal']))
                        except:
                            content.append(Paragraph(f"<b>Source URL:</b> {source_url}", styles['Normal']))
                    
                    # Content excerpt (shorter for conversation PDF) - ESCAPE HTML!
                    content_text = result.chunk.content
                    if len(content_text) > 400:
                        content_text = content_text[:400] + "..."
                    
                    # Clean and escape content for PDF
                    import re
                    # Remove any existing HTML tags
                    content_text = re.sub(r'<[^>]+>', '', content_text)
                    # Escape remaining special characters
                    content_text = html.escape(content_text)
                    
                    content.append(Paragraph(f"<b>Content:</b> {content_text}", styles['Normal']))
                    content.append(Spacer(1, 8))
                except Exception as e:
                    logger.error(f"Error adding source {j} in Sources Referenced section: {e}")
                    # Skip this source if there's an error
                    continue
        
        elif exchange.get('source_ids'):
            # Fallback for older entries
            content.append(Paragraph("Sources Referenced", heading_style))
            content.append(Paragraph(f"This exchange referenced {len(exchange['source_ids'])} sources (IDs: {', '.join(exchange['source_ids'][:5])}{'...' if len(exchange['source_ids']) > 5 else ''})", styles['Normal']))
        
        # Add page break between exchanges (except for the last one)
        if i < len(st.session_state.conversation_history) - 1:
            content.append(Spacer(1, 20))
            content.append(PageBreak())
    
    # Final footer
    content.append(Spacer(1, 30))
    footer_text = "Historical Newspaper Search - Complete Conversation History | " \
                 "Powered by sentence-transformers and Pinecone | " \
                 "Data sourced from Internet Archive historical newspapers"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    )
    content.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer


def generate_single_exchange_pdf(exchange_index: int) -> BytesIO:
    """Generate PDF for a single conversation exchange."""
    if not PDF_AVAILABLE:
        raise ImportError("PDF generation not available. Install reportlab: pip install reportlab")
    
    if exchange_index >= len(st.session_state.conversation_history):
        raise ValueError("Invalid exchange index")
    
    exchange = st.session_state.conversation_history[exchange_index]
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#2a5298')
    )
    
    # Build PDF content
    content = []
    
    # Title
    content.append(Paragraph(f"Historical Newspaper Search - Exchange {exchange_index + 1}", title_style))
    content.append(Spacer(1, 20))
    
    # Exchange Information
    content.append(Paragraph("Exchange Details", heading_style))
    
    search_type = "Unknown"
    if exchange.get('search_query'):
        search_type = exchange['search_query'].search_type.title()
    
    exchange_info = [
        ["Query:", exchange['query']],
        ["Timestamp:", exchange['timestamp'].strftime("%Y-%m-%d %H:%M:%S")],
        ["Search Type:", search_type],
        ["Sources Used:", str(len(exchange.get('source_ids', [])))]
    ]
    
    exchange_table = Table(exchange_info, colWidths=[2*inch, 4*inch])
    exchange_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    content.append(exchange_table)
    content.append(Spacer(1, 20))
    
    # AI Response if available
    if exchange.get('response'):
        content.append(Paragraph("AI Response", heading_style))
        
        # Parse and format AI response to preserve structure
        formatted_ai_content = parse_ai_response_for_pdf(exchange['response'], styles, exchange.get('sources', []))
        for element in formatted_ai_content:
            content.append(element)
        
        content.append(Spacer(1, 20))
    
    # Source Information with full details
    if exchange.get('sources'):
        content.append(Paragraph("Sources Referenced", heading_style))
        content.append(Paragraph(f"This exchange referenced {len(exchange['sources'])} unique sources from the historical newspaper database.", styles['Normal']))
        content.append(Spacer(1, 15))
        
        # Show detailed source information
        for i, result in enumerate(exchange['sources'], 1):
            # Source header
            source_header = f"Source {i}: {result.chunk.newspaper_metadata.newspaper_name} " \
                           f"(Relevance: {int(result.relevance_score * 100)}%)"
            content.append(Paragraph(source_header, styles['Heading4']))
            
            # Citation
            citation = result.format_citation()
            content.append(Paragraph(f"<b>Citation:</b> {citation}", styles['Normal']))
            
            # Internet Archive link if available
            source_url = result.chunk.newspaper_metadata.source_url
            if not source_url:
                source_url = reconstruct_internet_archive_url(result)
            if source_url:
                content.append(Paragraph(f"<b>Source URL:</b> <link href='{source_url}'>{source_url}</link>", styles['Normal']))
            
            # Content excerpt (limit for PDF readability)
            content_text = result.chunk.content
            if len(content_text) > 500:
                content_text = content_text[:500] + "..."
            
            content.append(Paragraph(f"<b>Content:</b> {content_text}", styles['Normal']))
            content.append(Spacer(1, 10))
    
    elif exchange.get('source_ids'):
        # Fallback for older entries without full source objects
        content.append(Paragraph("Sources Referenced", heading_style))
        content.append(Paragraph(f"This exchange referenced {len(exchange['source_ids'])} unique sources from the historical newspaper database.", styles['Normal']))
        content.append(Spacer(1, 10))
        
        for i, source_id in enumerate(exchange['source_ids'], 1):
            content.append(Paragraph(f"{i}. Source ID: {source_id}", styles['Normal']))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_text = "Historical Newspaper Search - Individual Exchange Report | " \
                 "Powered by sentence-transformers and Pinecone | " \
                 "Data sourced from Internet Archive historical newspapers"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    )
    content.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    return buffer


def generate_pdf_data() -> bytes:
    """Generate PDF data from session state."""
    if 'last_search' not in st.session_state:
        raise ValueError("No search data available for PDF generation")
    
    search_data = st.session_state.last_search
    pdf_buffer = generate_pdf_report(
        search_data['query_text'],
        search_data['search_query'],
        search_data['results'],
        search_data.get('ai_response'),
        search_data.get('source_analyses'),
        search_data.get('response_mode', 'Essay Generation')
    )
    return pdf_buffer.getvalue()


def generate_pdf_report(query_text: str, search_query: SearchQuery, results: List[SearchResult], ai_response: Optional[str] = None, source_analyses: Optional[List[Dict]] = None, response_mode: str = "Essay Generation") -> BytesIO:
    """Generate a PDF report of search results."""
    if not PDF_AVAILABLE:
        raise ImportError("PDF generation not available. Install reportlab: pip install reportlab")
    
    # Debug logging
    logger.info(f"PDF Report Generation - Mode: {response_mode}")
    logger.info(f"PDF Report - AI Response: {ai_response[:50] if ai_response else 'None'}")
    logger.info(f"PDF Report - Source Analyses: {len(source_analyses) if source_analyses else 'None'}")
    
    import re
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*inch)
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.HexColor('#2a5298')
    )
    
    # Build PDF content
    content = []
    
    # Title
    content.append(Paragraph("Historical Newspaper Search Report", title_style))
    content.append(Spacer(1, 20))
    
    # Search Information
    content.append(Paragraph("Search Details", heading_style))
    search_info = [
        ["Search Query:", query_text],
        ["Search Type:", search_query.search_type.title()],
        ["Date Range:", f"{search_query.start_date} to {search_query.end_date}"],
        ["Max Results:", str(search_query.max_results)],
        ["Relevance Threshold:", f"{search_query.relevance_threshold:.2f}"],
        ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    ]
    
    search_table = Table(search_info, colWidths=[2*inch, 4*inch])
    search_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
    ]))
    content.append(search_table)
    content.append(Spacer(1, 20))
    
    # AI Summary or Source Analysis
    logger.info(f"PDF - Checking conditions: mode={response_mode}, analyses={bool(source_analyses)}")
    if response_mode == "Source Analysis" and source_analyses:
        content.append(Paragraph("Source Analysis", heading_style))
        content.append(Spacer(1, 10))
        
        # Debug log
        logger.info(f"PDF Generation - Entering Source Analysis section with {len(source_analyses)} analyses")
        
        # Add each source analysis
        for i, analysis_data in enumerate(source_analyses, 1):
            logger.info(f"PDF - Processing source {i}, keys: {list(analysis_data.keys())}")
            result = analysis_data.get('result')
            analysis = analysis_data.get('analysis')
            
            if not result or not analysis:
                logger.error(f"PDF - Missing data for source {i}: result={bool(result)}, analysis={bool(analysis)}")
                continue
            
            # Source header
            header_text = f"Source {i}: {result.chunk.newspaper_metadata.newspaper_name} - {result.format_citation()}"
            content.append(Paragraph(header_text, styles['Heading3']))
            
            # Add Internet Archive link if available
            source_url = result.chunk.newspaper_metadata.source_url
            if not source_url:
                source_url = reconstruct_internet_archive_url(result)
            if source_url:
                content.append(Paragraph(f"<b>Source:</b> <link href='{source_url}'>{source_url}</link>", styles['Normal']))
                content.append(Spacer(1, 6))
            
            # Parse and format the analysis
            if analysis:
                logger.info(f"PDF - Processing analysis for source {i}: {len(analysis)} chars")
                # Split analysis into paragraphs and format
                paragraphs = analysis.split('\n\n')
                for para in paragraphs:
                    if para.strip():
                        # Handle markdown bold **text** - replace pairs properly
                        para = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', para)
                        # Handle bullet points
                        if para.strip().startswith('-') or para.strip().startswith('•'):
                            para = f"• {para.strip()[1:].strip()}"
                        
                        # Escape special characters for ReportLab  
                        # First handle ampersands
                        para = para.replace('&', '&amp;')
                        # Then handle less than/greater than (but not in our bold tags)
                        # Temporarily replace bold tags
                        para = para.replace('<b>', '|||BOLD_START|||')
                        para = para.replace('</b>', '|||BOLD_END|||')
                        # Now escape < and >
                        para = para.replace('<', '&lt;').replace('>', '&gt;')
                        # Restore bold tags
                        para = para.replace('|||BOLD_START|||', '<b>')
                        para = para.replace('|||BOLD_END|||', '</b>')
                        
                        try:
                            p = Paragraph(para, styles['Normal'])
                            content.append(p)
                            content.append(Spacer(1, 6))
                            logger.debug(f"Successfully added paragraph {len(content)} to PDF")
                        except Exception as e:
                            logger.error(f"Error adding paragraph to PDF: {e}")
                            logger.error(f"Problematic paragraph text: {para[:200]}...")
                            # Try simpler fallback - strip all tags and special chars
                            fallback_text = re.sub(r'<[^>]+>', '', para)
                            fallback_text = fallback_text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
                            try:
                                content.append(Paragraph(fallback_text, styles['Normal']))
                                content.append(Spacer(1, 6))
                                logger.info("Fallback paragraph succeeded")
                            except Exception as e2:
                                logger.error(f"Even fallback failed: {e2}")
                                # Last resort - add as plain text
                                content.append(Paragraph("Error displaying this section", styles['Normal']))
                                content.append(Spacer(1, 6))
            else:
                logger.warning(f"PDF - No analysis found for source {i}")
            
            content.append(Spacer(1, 15))
        
        content.append(Spacer(1, 20))
        
    elif ai_response and response_mode != "Source Analysis":
        content.append(Paragraph("AI Summary", heading_style))
        
        # Parse and format AI response to preserve structure  
        formatted_ai_content = parse_ai_response_for_pdf(ai_response, styles, results)
        for element in formatted_ai_content:
            content.append(element)
        
        content.append(Spacer(1, 20))
    
    # Debug fallback
    elif response_mode == "Source Analysis":
        logger.warning(f"Source Analysis mode but no analyses found. source_analyses: {source_analyses is not None}, length: {len(source_analyses) if source_analyses else 0}")
        content.append(Paragraph("Source Analysis", heading_style))
        content.append(Paragraph("No source analyses available.", styles['Normal']))
        content.append(Spacer(1, 20))
    
    # Results Summary
    content.append(Paragraph("Results Summary", heading_style))
    content.append(Paragraph(f"Found {len(results)} relevant results", styles['Normal']))
    content.append(Spacer(1, 20))
    
    # Individual Results
    content.append(Paragraph("Search Results", heading_style))
    
    for i, result in enumerate(results, 1):
        # Result header
        header_text = f"Source {i}: {result.chunk.newspaper_metadata.newspaper_name} " \
                     f"(Relevance: {int(result.relevance_score * 100)}%)"
        content.append(Paragraph(header_text, styles['Heading3']))
        
        # Citation
        citation = result.format_citation()
        content.append(Paragraph(f"<b>Citation:</b> {citation}", styles['Normal']))
        
        # Internet Archive link if available
        source_url = result.chunk.newspaper_metadata.source_url
        if not source_url:
            source_url = reconstruct_internet_archive_url(result)
        if source_url:
            content.append(Paragraph(f"<b>Source:</b> <link href='{source_url}'>{source_url}</link>", styles['Normal']))
        
        # Content
        # Limit content length for PDF and clean HTML
        content_text = result.chunk.content
        if len(content_text) > 1000:
            content_text = content_text[:1000] + "..."
        
        # Clean HTML tags and entities for PDF
        import html
        import re
        clean_content = html.unescape(content_text)
        # Remove HTML tags
        clean_content = re.sub(r'<[^>]+>', '', clean_content)
        # Remove problematic characters that could interfere with ReportLab
        clean_content = re.sub(r'[<>&]', '', clean_content)
        
        content.append(Paragraph(f"<b>Content:</b> {clean_content}", styles['Normal']))
        content.append(Spacer(1, 15))
    
    # Footer
    content.append(Spacer(1, 30))
    footer_text = "Historical Newspaper Search | Powered by sentence-transformers and Pinecone | " \
                 "Data sourced from Internet Archive historical newspapers"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    )
    content.append(Paragraph(footer_text, footer_style))
    
    # Build PDF
    logger.info(f"PDF - Building document with {len(content)} content items")
    try:
        doc.build(content)
        logger.info("PDF - Document built successfully")
    except Exception as e:
        logger.error(f"PDF - Error building document: {e}")
        raise
    buffer.seek(0)
    return buffer


def make_source_references_clickable(ai_response: str, search_results: List[SearchResult]) -> str:
    """Convert [Source N] references in AI responses to clickable hyperlinks."""
    if not ai_response or not search_results:
        return ai_response
    
    import re
    
    def replace_source_ref(match):
        source_num = int(match.group(1))
        # Source numbers are 1-indexed, list is 0-indexed
        if 1 <= source_num <= len(search_results):
            result = search_results[source_num - 1]
            
            # Get the Internet Archive URL
            source_url = result.chunk.newspaper_metadata.source_url
            if not source_url:
                source_url = reconstruct_internet_archive_url(result)
            
            if source_url:
                # Create clickable link
                return f'<a href="{source_url}" target="_blank" style="color: #0066cc; text-decoration: underline; font-weight: bold;">[Source {source_num}]</a>'
        
        # Return original if no URL found
        return match.group(0)
    
    # Find and replace all [Source N] references
    pattern = r'\[Source (\d+)\]'
    result = re.sub(pattern, replace_source_ref, ai_response)
    
    return result


def reconstruct_internet_archive_url(result: SearchResult) -> Optional[str]:
    """Reconstruct Internet Archive URL from existing metadata with error tracking."""
    try:
        meta = result.chunk.newspaper_metadata
        
        # Only handle Daily Worker for now
        if "Daily Worker" not in meta.newspaper_name and "The Worker" not in meta.newspaper_name:
            logger.debug(f"URL reconstruction not supported for: {meta.newspaper_name}")
            return None
        
        # Parse volume and issue from section field
        volume = None
        issue = None
        
        if meta.section and meta.section != "Unknown":
            # Extract volume and issue from patterns like "Volume 2, Issue 70"
            volume_issue_match = re.match(r'Volume (\d+), Issue (\d+)', meta.section)
            if volume_issue_match:
                volume = volume_issue_match.group(1)
                issue = volume_issue_match.group(2)
        
        # If we couldn't get volume/issue from section, try to construct a simpler URL
        # Many Internet Archive Daily Worker items use just the date pattern
        if not volume or not issue:
            logger.debug(f"Using date-only pattern for URL reconstruction: {meta.newspaper_name} {meta.publication_date}")
            # Fallback to date-only pattern - let's try to construct a basic URL
            date_str = meta.publication_date.strftime('%Y-%m-%d')
            year = meta.publication_date.year
            
            # Use appropriate pattern based on date when volume/issue are missing
            if ((year == 1924) or (year == 1925) or (year == 1928) or (year >= 1954 and year <= 1958)):
                possible_ids = [f"per_daily-worker_{date_str}"]
            elif (year >= 1926 and year <= 1927):
                possible_ids = [f"per_daily-worker_the-daily-worker_{date_str}"]
            elif (("The Worker" in meta.newspaper_name and "Daily" not in meta.newspaper_name) or 
                  (year >= 1948 and year <= 1953 and meta.publication_date.weekday() == 6)):
                possible_ids = [f"per_daily-worker_the-worker_{date_str}"]
            elif (year >= 1929 and year <= 1953):
                possible_ids = [f"per_daily-worker_daily-worker_{date_str}"]
            else:
                possible_ids = [f"per_daily-worker_{date_str}"]
            
            # Return the first pattern as a best guess
            url = f"https://archive.org/details/{possible_ids[0]}"
            logger.debug(f"Fallback URL (no volume/issue): {url}")
            return url
        
        # Format the date as YYYY-MM-DD
        date_str = meta.publication_date.strftime('%Y-%m-%d')
        
        # Determine the pattern based on date according to the documentation
        year = meta.publication_date.year
        month = meta.publication_date.month
        day = meta.publication_date.day
        
        # Method 1: Multiple date ranges (check first to avoid conflicts)
        if ((year == 1924) or 
            (year == 1925) or
            (year == 1928) or
            (year >= 1954 and year <= 1958)):
            archive_id = f"per_daily-worker_{date_str}_{volume}_{issue}"
        
        # Method 3: 1926-01-02 to 1927-12-31
        elif (year >= 1926 and year <= 1927):
            archive_id = f"per_daily-worker_the-daily-worker_{date_str}_{volume}_{issue}"
        
        # Method 4: Sunday editions of "The Worker" (1948-07-04 to 1953-12-27)
        # This is a special case within the Method 2 date range
        elif (("The Worker" in meta.newspaper_name and "Daily" not in meta.newspaper_name) or 
              (year >= 1948 and year <= 1953 and meta.publication_date.weekday() == 6)):  # Sunday = 6
            archive_id = f"per_daily-worker_the-worker_{date_str}_{volume}_{issue}"
        
        # Method 2: 1929-01-01 to 1953-12-31 (default for this range, includes non-Sunday 1948-53)
        elif (year >= 1929 and year <= 1953):
            archive_id = f"per_daily-worker_daily-worker_{date_str}_{volume}_{issue}"
        
        else:
            # Default fallback to Method 1
            logger.warning(f"Date {date_str} doesn't match known patterns, using Method 1")
            archive_id = f"per_daily-worker_{date_str}_{volume}_{issue}"
        
        url = f"https://archive.org/details/{archive_id}"
        logger.debug(f"Reconstructed URL: {url} for {meta.newspaper_name} {meta.publication_date}")
        return url
        
    except Exception as e:
        logger.error(f"Error reconstructing URL for {result.chunk.newspaper_metadata.newspaper_name} "
                    f"{result.chunk.newspaper_metadata.publication_date}: {e}")
        return None


def download_bm25_index(bm25_path: Path) -> bool:
    """Download BM25 index from Google Drive if not present."""
    if bm25_path.exists():
        return True
    
    # Google Drive file ID from the sharing link
    file_id = "1ujeMPLPFYhIMT8xei2ZcApcNvo-gZL-A"
    url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        # Create directory if it doesn't exist
        bm25_path.parent.mkdir(parents=True, exist_ok=True)
        
        with st.spinner("Downloading BM25 index (1.5GB) for keyword search capability... This is a one-time download."):
            # Use gdown to handle Google Drive downloads
            import gdown
            gdown.download(url, str(bm25_path), quiet=False)
            
        st.success("BM25 index downloaded successfully!")
        return True
        
    except Exception as e:
        st.warning(f"Could not download BM25 index: {e}. Continuing without keyword search.")
        logger.error(f"BM25 download error: {e}")
        return False


@st.cache_resource
def initialize_vector_db():
    """Initialize vector database connection."""
    try:
        # Validate configuration
        config.validate()
        
        # Initialize hosted vector database
        vector_db = VectorDatabaseHosted()
        
        # Load BM25 index if available
        # Use absolute path based on script location
        script_dir = Path(__file__).parent
        bm25_path = script_dir / "processed_data" / "bm25_index_hosted.pkl"
        
        logger.info(f"Looking for BM25 index at: {bm25_path}")
        
        # Skip BM25 download on cloud deployment due to memory constraints
        # Try to download if not present and we're not on Streamlit Cloud
        is_cloud_deployment = os.getenv('STREAMLIT_SHARING_MODE') or '/mount/src/' in str(bm25_path)
        
        if not bm25_path.exists() and not is_cloud_deployment:
            logger.info("BM25 index not found locally, attempting to download...")
            download_bm25_index(bm25_path)
        elif is_cloud_deployment:
            logger.info("Cloud deployment detected - skipping BM25 download due to memory constraints")
        
        if bm25_path.exists():
            try:
                logger.info(f"Loading BM25 index from: {bm25_path}")
                # Show loading message to user
                with st.spinner("Loading BM25 index for keyword search (this may take a moment)..."):
                    vector_db.load_bm25_index(str(bm25_path))
                st.success("Connected to Pinecone with full search capabilities including BM25 keyword search")
                logger.info("BM25 index loaded successfully")
            except MemoryError as e:
                st.warning("BM25 index too large for available memory. Continuing with semantic search only.")
                logger.error(f"Memory error loading BM25 index: {e}")
            except Exception as e:
                st.warning(f"Failed to load BM25 index: {e}. Continuing with semantic search only.")
                logger.error(f"BM25 index loading error: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            st.info("BM25 index not available. Using semantic search only.")
            logger.info(f"BM25 index file not found at: {bm25_path}")
        
        return vector_db
    except Exception as e:
        st.error(f"Failed to initialize vector database: {e}")
        return None


def format_search_result(result: SearchResult, index: int) -> str:
    """Format a search result for display."""
    import html
    
    citation = result.format_citation()
    score_percent = int(result.relevance_score * 100)
    
    # Try to get source URL from metadata first, then try reconstruction
    source_url = result.chunk.newspaper_metadata.source_url
    if not source_url:
        source_url = reconstruct_internet_archive_url(result)
    
    # Create source link if URL is available
    source_link = ""
    if source_url:
        source_link = f' <a href="{source_url}" target="_blank" style="color: #0066cc; text-decoration: none;">[View Source]</a>'
    
    # Clean up the content by unescaping HTML entities and removing any stray HTML tags
    clean_content = html.unescape(result.chunk.content)
    # Remove any remaining HTML tags that shouldn't be there
    clean_content = re.sub(r'<[^>]+>', '', clean_content)
    
    return f"""
    <div class="search-result">
        <div class="result-header">
            Source {index}: {result.chunk.newspaper_metadata.newspaper_name}
            <span class="relevance-score">Relevance: {score_percent}%</span>
            {source_link}
        </div>
        <div class="result-citation">{citation}</div>
        <div class="result-content">{clean_content}</div>
    </div>
    """


def initialize_conversation_state():
    """Initialize conversation state in session."""
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    if 'used_sources' not in st.session_state:
        st.session_state.used_sources = set()
    if 'conversation_context' not in st.session_state:
        st.session_state.conversation_context = ""

def add_to_conversation(query: str, ai_response: str, sources: List[SearchResult], search_query: SearchQuery = None, source_analyses: List[Dict] = None, response_mode: str = "Essay Generation"):
    """Add a query-response pair to conversation history."""
    conversation_entry = {
        'query': query,
        'response': ai_response,
        'timestamp': datetime.now(),
        'source_ids': [result.chunk.chunk_id for result in sources],
        'sources': sources,  # Store full SearchResult objects for PDF generation
        'search_query': search_query,  # Store search query for PDF generation
        'source_analyses': source_analyses,  # Store source analyses for Source Analysis mode
        'response_mode': response_mode  # Store response mode
    }
    st.session_state.conversation_history.append(conversation_entry)
    
    # Update used sources
    for result in sources:
        st.session_state.used_sources.add(result.chunk.chunk_id)
    
    # Update conversation context (keep last 3 exchanges for context)
    recent_history = st.session_state.conversation_history[-3:]
    context_parts = []
    for entry in recent_history:
        context_parts.append(f"Q: {entry['query']}")
        if entry['response']:
            # Truncate long responses for context
            response_summary = entry['response'][:200] + "..." if len(entry['response']) > 200 else entry['response']
            context_parts.append(f"A: {response_summary}")
    
    st.session_state.conversation_context = "\n".join(context_parts)

def enhance_query_with_context(current_query: str) -> str:
    """Enhance current query with conversation context."""
    if not st.session_state.conversation_context:
        return current_query
    
    # Create enhanced query that includes context
    enhanced_query = f"""Based on our previous discussion about:
{st.session_state.conversation_context}

New question: {current_query}"""
    
    return enhanced_query

def safe_pdf_download_button(usage_monitor: UsageMonitor, **kwargs) -> bool:
    """Wrapper for st.download_button that checks usage limits first."""
    # Check if user can download PDF
    if not usage_monitor.check_pdf_limit():
        return False
    
    # Show the download button
    if st.download_button(**kwargs):
        # Record the download
        usage_monitor.record_pdf_download()
        return True
    return False


def get_pdf_context(result: SearchResult) -> Dict[str, Any]:
    """Get PDF context for the main chunk by fetching the source PDF URL."""
    meta = result.chunk.newspaper_metadata
    
    # Get the Internet Archive URL
    source_url = result.chunk.newspaper_metadata.source_url
    if not source_url:
        source_url = reconstruct_internet_archive_url(result)
    
    if not source_url:
        logger.warning(f"Could not reconstruct Internet Archive URL for chunk")
        return {"main_chunk": result, "pdf_url": None}
    
    # Convert details URL to PDF URL
    # Pattern: /details/ID/ -> /download/ID/ID.pdf
    if "/details/" in source_url:
        # Extract the ID from the details URL
        parts = source_url.strip('/').split('/')
        if parts[-2] == "details" and len(parts) >= 2:
            archive_id = parts[-1]
            # Construct PDF URL using the pattern you provided
            pdf_url = f"https://dn721601.ca.archive.org/0/items/{archive_id}/{archive_id}.pdf"
            
            return {
                "main_chunk": result,
                "pdf_url": pdf_url,
                "archive_url": source_url
            }
    
    return {"main_chunk": result, "pdf_url": None}


def apply_source_diversification(results: List[SearchResult], diversity_weight: float = 0.3) -> List[SearchResult]:
    """Apply source diversification by penalizing previously used sources."""
    if not st.session_state.used_sources:
        return results
    
    diversified_results = []
    
    for result in results:
        # Create a copy to avoid modifying original
        new_result = SearchResult(
            chunk=result.chunk,
            relevance_score=result.relevance_score,
            highlights=result.highlights
        )
        
        # Apply penalty if source was used before
        if result.chunk.chunk_id in st.session_state.used_sources:
            # Reduce score but don't eliminate completely
            penalty = diversity_weight * result.relevance_score
            new_result.relevance_score = max(0.1, result.relevance_score - penalty)
        
        # Small bonus for sources from different dates
        if st.session_state.conversation_history:
            last_sources = []
            for entry in st.session_state.conversation_history[-2:]:  # Last 2 exchanges
                for source_id in entry.get('source_ids', []):
                    last_sources.append(source_id)
            
            # Check if this result is from a different publication date
            current_date = result.chunk.newspaper_metadata.publication_date
            different_date = True
            for entry in st.session_state.conversation_history[-1:]:
                # This is simplified - in practice you'd check actual dates
                if result.chunk.chunk_id in entry.get('source_ids', []):
                    different_date = False
                    break
            
            if different_date and result.chunk.chunk_id not in st.session_state.used_sources:
                # Small boost for diverse dates
                new_result.relevance_score = min(1.0, new_result.relevance_score + 0.05)
        
        diversified_results.append(new_result)
    
    # Re-sort by adjusted scores
    diversified_results.sort(key=lambda x: x.relevance_score, reverse=True)
    return diversified_results

def main():
    # Initialize auth manager
    auth = AuthManager()
    
    # Require authentication
    auth.require_authentication()
    
    # Initialize usage monitor
    usage_monitor = UsageMonitor()
    
    # Show authentication status and usage in sidebar
    with st.sidebar:
        if st.session_state.get('authenticated'):
            st.write("**🔓 Authenticated**")
            if st.button("Logout", use_container_width=True):
                auth.logout()
                st.rerun()
            
            # Show usage statistics
            usage_monitor.display_usage_sidebar()
    
    # Initialize conversation state
    initialize_conversation_state()
    
    # Header with Daily Worker masthead
    # Try local path first, then use Google Drive URL
    masthead_path = Path(__file__).parent / "ilovepdf_pages-to-jpg" / "per_daily-worker_daily-worker_1935-01-01_12_1_page-0001.jpg"
    
    if masthead_path.exists():
        # Read and encode the local image
        with open(masthead_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()
        masthead_img_src = f"data:image/jpeg;base64,{img_base64}"
    else:
        # Use fallback approach for cloud deployment - try multiple methods
        # Method 1: Google Drive direct link (may require public sharing)
        gdrive_file_id = "1aFE1IZ9Z3EHs5TTZ8CTJv5vFpWpOU1On"
        
        # Try the thumbnail view which is more reliable for public images
        masthead_img_src = f"https://drive.google.com/thumbnail?id={gdrive_file_id}&sz=w400"
        
        # Alternative: Use a base64 encoded placeholder or external hosting
        # If Google Drive fails, we could fallback to a simple text header
    
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; align-items: center; justify-content: center; gap: 2rem; flex-wrap: wrap;">
            <div style="flex: 1; text-align: center; min-width: 300px;">
                <h1>AI-powered Daily Worker (1924-58) Search Database</h1>
                <p>Query across the CPUSA's Daily Worker, as preserved on <a href="https://archive.org/details/pub_daily-worker?and%5B%5D=year%3A%5B1934+TO+1936%5D" target="_blank" style="color: #ffffff; text-decoration: underline;">Internet Archive</a></p>
            </div>
            <div style="flex: 0 0 auto;">
                <img src="{masthead_img_src}" 
                     alt="Daily Worker Masthead from January 1, 1935" 
                     style="max-height: 120px; width: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); 
                            object-fit: contain; object-position: top;"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display: none; background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; 
                           text-align: center; color: #ffffff; border: 2px solid rgba(255,255,255,0.3);">
                    <strong>Daily Worker</strong><br>
                    <small>January 1, 1935</small>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick navigation info
    st.info("**New to the system?** Check the 'How to Use' page in the sidebar for search tips and examples.")
    
    # Create placeholder for conversation history at the top
    conversation_history_placeholder = st.empty()
    
    # Initialize vector database
    vector_db = initialize_vector_db()
    
    if not vector_db:
        st.error("Unable to connect to the vector database. Please check your configuration.")
        st.stop()
    
    # Sidebar filters
    with st.sidebar:
        st.header("Search Filters")
        
        # Add navigation link to How to Use page
        st.markdown("---")
        st.markdown("**Need help?** See the 'How to Use' page in the sidebar for tips and examples.")
        
        # Date range filter
        st.subheader("Date Range")
        
        # Default date range (extent of newspaper coverage)
        default_start = date(1924, 1, 5)  # First available newspaper
        default_end = date(1958, 1, 26)   # Last available newspaper
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From",
                value=default_start,
                min_value=date(1800, 1, 1),
                max_value=date.today()
            )
        
        with col2:
            end_date = st.date_input(
                "To",
                value=default_end,
                min_value=date(1800, 1, 1),
                max_value=date.today()
            )
        
        # Search type
        st.subheader("Search Type")
        
        # Check if BM25 is available
        bm25_available = hasattr(vector_db, 'bm25') and vector_db.bm25 is not None
        
        if bm25_available:
            search_options = ["Hybrid (Recommended)", "Semantic", "Keyword"]
            help_text = """
            - **Hybrid**: Combines semantic understanding with keyword matching
            - **Semantic**: Finds conceptually similar content
            - **Keyword**: Traditional keyword-based search
            """
        else:
            search_options = ["Semantic (Recommended)"]
            help_text = """
            - **Semantic**: Finds conceptually similar content using AI embeddings
            
            Note: Keyword search temporarily unavailable in cloud deployment due to memory constraints.
            """
        
        search_type = st.radio(
            "Select search method",
            search_options,
            help=help_text
        )
        
        # Advanced options
        with st.expander("Advanced Options"):
            max_results = st.slider(
                "Maximum results",
                min_value=5,
                max_value=50,
                value=20,
                step=5,
                help="Maximum number of text chunks retrieved per search. Each chunk is a section of newspaper content that may contain part of an article or multiple short items."
            )
            
            relevance_threshold = st.slider(
                "Relevance threshold",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.05,
                help="Minimum relevance score to include results"
            )
            
            # Response Mode Selection
            st.markdown("**Response Mode**")
            
            response_mode = st.radio(
                "Select how to process results",
                ["Essay Generation", "Source Analysis"],
                help="""
                - **Essay Generation**: AI synthesizes all results into a comprehensive answer
                - **Source Analysis**: AI analyzes each source individually with surrounding context
                """
            )
            
            # Only show AI enhancement option for Essay Generation mode
            if response_mode == "Essay Generation":
                use_ai_enhancement = st.checkbox(
                    "Enhanced AI Summary (Gemini)",
                    value=True if config.GEMINI_API_KEY else False,
                    help="Use Gemini AI to synthesize search results into a comprehensive answer",
                    disabled=not config.GEMINI_API_KEY
                )
                
                if not config.GEMINI_API_KEY and use_ai_enhancement:
                    st.warning("Add GEMINI_API_KEY to .env file to enable AI summaries")
            else:
                # Source Analysis mode always uses AI
                use_ai_enhancement = True
                if not config.GEMINI_API_KEY:
                    st.warning("Source Analysis mode requires GEMINI_API_KEY in .env file")
            
    
    # Show conversation history if it exists
    
    # Show context awareness info
    if st.session_state.conversation_context:
        st.info("**Conversational mode active** - Your next query will be answered with context from previous questions.")
    
    # Main search interface
    search_container = st.container()
    
    with search_container:
        # Search input
        query_text = st.text_input(
            "Search Query",
            placeholder="Enter your search terms...",
            help="Search for topics, people, events, or keywords in historical newspapers"
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search_button = st.button("Search", type="primary", use_container_width=True)
        with col2:
            clear_button = st.button("Clear Results", use_container_width=True)
        with col3:
            if st.session_state.conversation_history:
                clear_conversation_button = st.button("Clear History", use_container_width=True)
            else:
                clear_conversation_button = False
        
        # Check if we should display previous results (after PDF download)
        if 'last_search' in st.session_state and not (search_button and query_text):
            # Display previous results if they exist and no new search is being performed
            previous_data = st.session_state.last_search
            
            # Show success message for previous search
            st.success(f"Previous search results for: '{previous_data['query_text']}'")
            
            # Show AI summary or Source Analysis based on mode
            response_mode = previous_data.get('response_mode', 'Essay Generation')
            
            if response_mode == "Source Analysis" and previous_data.get('source_analyses'):
                st.markdown("### Source Analysis")
                for i, analysis_data in enumerate(previous_data['source_analyses'], 1):
                    result = analysis_data['result']
                    analysis = analysis_data['analysis']
                    
                    # Create expandable section for each source
                    with st.expander(f"Source {i}: {result.chunk.newspaper_metadata.newspaper_name} - {result.format_citation()}", expanded=i<3):
                        st.markdown(analysis)
                        
                        # Add link to Internet Archive if available
                        source_url = result.chunk.newspaper_metadata.source_url
                        if not source_url:
                            source_url = reconstruct_internet_archive_url(result)
                        if source_url:
                            st.markdown(f"[View in Internet Archive]({source_url})")
                st.markdown("---")
                
            elif previous_data.get('ai_response'):
                st.markdown("### AI Summary")
                with st.container():
                    # Make source references clickable for previous search results
                    clickable_response = make_source_references_clickable(previous_data['ai_response'], previous_data['results'])
                    st.markdown(
                        f'<div style="background-color: #f0f8ff; padding: 1.5rem; '
                        f'border-radius: 10px; border-left: 4px solid #4285f4;">'
                        f'{clickable_response}</div>',
                        unsafe_allow_html=True
                    )
                st.markdown("---")
            
            # Show PDF download button
            if PDF_AVAILABLE:
                try:
                    if response_mode == "Source Analysis" and previous_data.get('source_analyses'):
                        button_label = "Download Complete Report with Source Analysis as PDF"
                        button_help = "Download search results with individual source analyses as PDF"
                    elif previous_data.get('ai_response'):
                        button_label = "Download Complete Report with AI Summary as PDF"
                        button_help = "Download complete search results with AI summary as PDF"
                    else:
                        button_label = "Download Report as PDF"
                        button_help = "Download search results as a formatted PDF report"
                    
                    pdf_buffer = generate_pdf_report(
                        previous_data['query_text'],
                        previous_data['search_query'],
                        previous_data['results'],
                        previous_data.get('ai_response'),
                        previous_data.get('source_analyses'),
                        previous_data.get('response_mode', 'Essay Generation')
                    )
                    st.download_button(
                        label=button_label,
                        data=pdf_buffer.getvalue(),
                        file_name=f"newspaper_search_report_{previous_data['timestamp']}.pdf",
                        mime="application/pdf",
                        help=button_help,
                        key="pdf_download_preserved"
                    )
                except Exception as e:
                    logger.error(f"PDF generation error: {e}")
                    st.warning("PDF generation temporarily unavailable.")
            
            # Show search results
            st.markdown("### Search Results")
            for i, result in enumerate(previous_data['results'], 1):
                st.markdown(
                    format_search_result(result, i),
                    unsafe_allow_html=True
                )
        
        # Handle search
        elif search_button and query_text:
            # Check usage limits first
            if not usage_monitor.check_search_limit():
                st.stop()
            
            # Check cost threshold
            if not usage_monitor.check_cost_threshold():
                st.stop()
            
            # Map search type selection
            search_type_map = {
                "Hybrid (Recommended)": "hybrid",
                "Semantic": "semantic",
                "Semantic (Recommended)": "semantic",
                "Keyword": "keyword"
            }
            
            # Create search query
            search_query = SearchQuery(
                query_text=query_text,
                start_date=start_date,
                end_date=end_date,
                max_results=max_results,
                relevance_threshold=relevance_threshold,
                search_type=search_type_map[search_type]
            )
            
            # Enhance query with conversation context for AI
            enhanced_query_for_search = query_text  # Keep original for vector search
            enhanced_query_for_ai = enhance_query_with_context(query_text)
            
            # Show search progress
            with st.spinner(f"Searching for '{query_text}'..."):
                try:
                    results = vector_db.search(search_query)
                    
                    if results:
                        # Apply source diversification
                        results = apply_source_diversification(results)
                        
                        # Track URL reconstruction statistics
                        url_stats = {"total": len(results), "reconstructed": 0, "failed": 0}
                        for result in results:
                            if result.chunk.newspaper_metadata.source_url:
                                continue  # Already has URL
                            reconstructed_url = reconstruct_internet_archive_url(result)
                            if reconstructed_url:
                                url_stats["reconstructed"] += 1
                            else:
                                url_stats["failed"] += 1
                        
                        # Calculate diversity stats
                        previously_used_count = sum(1 for r in results if r.chunk.chunk_id in st.session_state.used_sources)
                        new_sources_count = len(results) - previously_used_count
                        
                        success_msg = f"Found {len(results)} relevant results"
                        if url_stats["reconstructed"] > 0:
                            success_msg += f" • {url_stats['reconstructed']} Internet Archive links available"
                        if url_stats["failed"] > 0:
                            success_msg += f" • {url_stats['failed']} sources without links"
                        
                        # Add diversification info if in conversation mode
                        if st.session_state.conversation_history:
                            success_msg += f" • {new_sources_count} new sources, {previously_used_count} previously used (de-prioritized)"
                        
                        st.success(success_msg)
                        
                        # Record the search for usage tracking
                        usage_monitor.record_search(used_ai=use_ai_enhancement)
                        
                        # Handle different response modes
                        ai_response = None
                        source_analyses = []
                        
                        if use_ai_enhancement and config.GEMINI_API_KEY:
                            if response_mode == "Essay Generation":
                                # Traditional essay generation mode
                                try:
                                    with st.spinner("Generating AI summary..."):
                                        response_gen = ResponseGenerator()
                                        ai_response = response_gen.generate_response(
                                            enhanced_query_for_ai,  # Use enhanced query for AI
                                            results,
                                            max_results_to_use=min(max_results, len(results))
                                        )
                                        
                                    if ai_response:
                                        st.markdown("### AI Summary")
                                        with st.container():
                                            # Make source references clickable
                                            clickable_response = make_source_references_clickable(ai_response, results)
                                            st.markdown(
                                                f'<div style="background-color: #f0f8ff; padding: 1.5rem; '
                                                f'border-radius: 10px; border-left: 4px solid #4285f4;">'
                                                f'{clickable_response}</div>',
                                                unsafe_allow_html=True
                                            )
                                        st.markdown("---")
                                                
                                except Exception as e:
                                    st.error(f"Error generating AI summary: {e}")
                            
                            elif response_mode == "Source Analysis":
                                # New source analysis mode
                                try:
                                    with st.spinner(f"Analyzing {len(results)} sources with PDF context..."):
                                        import concurrent.futures
                                        import threading
                                        
                                        response_gen = ResponseGenerator()
                                        
                                        # Create a thread-local storage for response generators
                                        thread_local = threading.local()
                                        
                                        def analyze_single_source(result):
                                            """Analyze a single source in parallel."""
                                            try:
                                                # Each thread gets its own ResponseGenerator instance
                                                if not hasattr(thread_local, 'response_gen'):
                                                    thread_local.response_gen = ResponseGenerator()
                                                
                                                # Get PDF context
                                                pdf_context = get_pdf_context(result)
                                                
                                                # Generate analysis
                                                analysis = thread_local.response_gen.generate_source_analysis(
                                                    enhanced_query_for_ai,
                                                    result,
                                                    pdf_context
                                                )
                                                
                                                if analysis:
                                                    return {
                                                        'result': result,
                                                        'analysis': analysis,
                                                        'pdf_context': pdf_context
                                                    }
                                                return None
                                            except Exception as e:
                                                logger.error(f"Error analyzing source: {e}")
                                                return None
                                        
                                        # Process all sources in parallel
                                        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                                            # Submit all tasks
                                            future_to_result = {
                                                executor.submit(analyze_single_source, result): i 
                                                for i, result in enumerate(results)
                                            }
                                            
                                            # Collect results as they complete
                                            for future in concurrent.futures.as_completed(future_to_result):
                                                result_data = future.result()
                                                if result_data:
                                                    source_analyses.append(result_data)
                                        
                                        # Sort analyses by original order
                                        source_analyses.sort(key=lambda x: results.index(x['result']))
                                        
                                        # Display source analyses
                                        if source_analyses:
                                            st.markdown("### Source Analysis")
                                            for i, analysis_data in enumerate(source_analyses):
                                                result = analysis_data['result']
                                                analysis = analysis_data['analysis']
                                                
                                                # Create expandable section for each source
                                                with st.expander(f"Source {i+1}: {result.chunk.newspaper_metadata.newspaper_name} - {result.format_citation()}", expanded=i<3):
                                                    st.markdown(analysis)
                                                    
                                                    # Add link to Internet Archive if available
                                                    source_url = result.chunk.newspaper_metadata.source_url
                                                    if not source_url:
                                                        source_url = reconstruct_internet_archive_url(result)
                                                    if source_url:
                                                        st.markdown(f"📰 [View on Internet Archive]({source_url})")
                                            st.markdown("---")
                                                
                                except Exception as e:
                                    st.error(f"Error generating source analysis: {e}")
                        
                        # Add to conversation history
                        if response_mode == "Essay Generation":
                            add_to_conversation(query_text, ai_response or "", results, search_query)
                        else:
                            # For Source Analysis, create a summary for conversation history but also store the analyses
                            analysis_summary = f"Source Analysis: {len(source_analyses)} sources analyzed"
                            add_to_conversation(query_text, analysis_summary, results, search_query, source_analyses, response_mode)
                        
                        # Store results and AI response in session state for PDF generation
                        # For Source Analysis mode, don't store ai_response to ensure PDF uses source_analyses
                        if response_mode == "Source Analysis":
                            ai_response_for_storage = None
                        else:
                            ai_response_for_storage = ai_response
                            
                        st.session_state.last_search = {
                            'query_text': query_text,
                            'search_query': search_query,
                            'results': results,
                            'ai_response': ai_response_for_storage,
                            'source_analyses': source_analyses,
                            'response_mode': response_mode,
                            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
                        }
                        
                        # Add PDF download button AFTER AI summary is complete
                        if PDF_AVAILABLE:
                            try:
                                # Download button with appropriate label
                                if response_mode == "Source Analysis" and source_analyses:
                                    button_label = "Download Complete Report with Source Analysis as PDF"
                                    button_help = "Download search results with individual source analyses as PDF"
                                elif ai_response:
                                    button_label = "Download Complete Report with AI Summary as PDF"
                                    button_help = "Download complete search results with AI summary as PDF"
                                else:
                                    button_label = "Download Report as PDF"
                                    button_help = "Download search results as a formatted PDF report"
                                
                                pdf_buffer = generate_pdf_report(
                                    query_text,
                                    search_query,
                                    results,
                                    ai_response,
                                    source_analyses,
                                    response_mode
                                )
                                if st.download_button(
                                    label=button_label,
                                    data=pdf_buffer.getvalue(),
                                    file_name=f"newspaper_search_report_{st.session_state.last_search['timestamp']}.pdf",
                                    mime="application/pdf",
                                    help=button_help,
                                    key="pdf_download"
                                ):
                                    # This block runs after download, but we don't need to do anything
                                    pass
                                
                            except Exception as e:
                                logger.error(f"PDF generation error: {e}")
                                st.warning("PDF generation temporarily unavailable.")
                        else:
                            st.info("PDF download requires reportlab library. Install with: pip install reportlab")
                        
                        # Display results
                        st.markdown("### Search Results")
                        
                        for i, result in enumerate(results, 1):
                            st.markdown(
                                format_search_result(result, i),
                                unsafe_allow_html=True
                            )
                    else:
                        st.info("No results found matching your search criteria. Try adjusting your filters or search terms.")
                
                except Exception as e:
                    st.error(f"An error occurred during search: {e}")
                    logger.error(f"Search error: {e}")
        
        # Handle clear results
        if clear_button:
            # Clear search results but keep conversation history
            if 'last_search' in st.session_state:
                del st.session_state.last_search
            st.rerun()
        
        # Handle clear conversation history
        if clear_conversation_button:
            # Clear conversation history and used sources
            st.session_state.conversation_history = []
            st.session_state.used_sources = set()
            st.session_state.conversation_context = ""
            if 'last_search' in st.session_state:
                del st.session_state.last_search
            st.success("Conversation history cleared. Starting fresh!")
            st.rerun()
    # Render conversation history in the placeholder at the top
    with conversation_history_placeholder.container():
        if st.session_state.conversation_history:
            # Add download button for full conversation PDF
            col1, col2 = st.columns([1, 4])
            with col1:
                if PDF_AVAILABLE:
                    try:
                        conversation_pdf_buffer = generate_full_conversation_pdf()
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"full_conversation_{timestamp}.pdf"
                        
                        st.download_button(
                            label="Download Full Conversation PDF",
                            data=conversation_pdf_buffer.getvalue(),
                            file_name=filename,
                            mime="application/pdf",
                            help="Download complete conversation history with all exchanges and sources",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Error generating conversation PDF: {e}")
                else:
                    st.info("Install reportlab for PDF download")
            
            with st.expander(f"Conversation History ({len(st.session_state.conversation_history)} exchanges)", expanded=False):
                for i, entry in enumerate(st.session_state.conversation_history):
                    exchange_num = i + 1
                    
                    # Create columns for exchange header
                    col1, col2, col3 = st.columns([4, 1, 1])
                    
                    with col1:
                        st.markdown(f"**Exchange {exchange_num}** - {entry['timestamp'].strftime('%m/%d %H:%M')}")
                        st.markdown(f"**Q:** {entry['query']}")
                    
                    with col2:
                        # Expand/collapse button for full response
                        expand_key = f"expand_exchange_{i}"
                        if expand_key not in st.session_state:
                            st.session_state[expand_key] = False
                        
                        if st.button("Expand" if not st.session_state[expand_key] else "Collapse", 
                                   key=f"expand_btn_{i}", 
                                   use_container_width=True):
                            st.session_state[expand_key] = not st.session_state[expand_key]
                    
                    with col3:
                        # PDF download button for individual exchange
                        if PDF_AVAILABLE:
                            try:
                                pdf_buffer = generate_single_exchange_pdf(i)
                                timestamp = entry['timestamp'].strftime("%Y%m%d_%H%M%S")
                                filename = f"exchange_{exchange_num}_{timestamp}.pdf"
                                
                                st.download_button(
                                    label="PDF",
                                    data=pdf_buffer.getvalue(),
                                    file_name=filename,
                                    mime="application/pdf",
                                    key=f"download_exchange_{i}",
                                    use_container_width=True
                                )
                            except Exception as e:
                                st.error(f"Error: {str(e)[:20]}...")
                    
                    # Show response (expanded or truncated)
                    if entry['response']:
                        if st.session_state.get(expand_key, False):
                            # Show full response with proper formatting
                            st.markdown("**Full Response:**")
                            with st.container():
                                # Make source references clickable for conversation history
                                sources_for_entry = entry.get('sources', [])
                                clickable_response = make_source_references_clickable(entry['response'], sources_for_entry)
                                st.markdown(
                                    f'<div style="background-color: #f0f8ff; padding: 1rem; '
                                    f'border-radius: 8px; border-left: 3px solid #4285f4; '
                                    f'max-height: 400px; overflow-y: auto;">'
                                    f'{clickable_response}</div>',
                                    unsafe_allow_html=True
                                )
                            # Show source details if available
                            if entry.get('sources'):
                                st.markdown(f"*Sources used: {len(entry['sources'])}*")
                                # Show first few sources with details
                                for i, source in enumerate(entry['sources'][:3], 1):
                                    citation = source.format_citation()
                                    st.markdown(f"**Source {i}:** {source.chunk.newspaper_metadata.newspaper_name} - {citation}")
                                if len(entry['sources']) > 3:
                                    st.markdown(f"*...and {len(entry['sources']) - 3} more sources*")
                            else:
                                # Fallback for older entries
                                st.markdown(f"*Sources used: {len(entry['source_ids'])} | Source IDs: {', '.join(entry['source_ids'][:3])}{'...' if len(entry['source_ids']) > 3 else ''}*")
                        else:
                            # Show truncated response
                            response_preview = entry['response'][:200] + "..." if len(entry['response']) > 200 else entry['response']
                            # Make source references clickable in preview too
                            sources_for_entry = entry.get('sources', [])
                            clickable_preview = make_source_references_clickable(response_preview, sources_for_entry)
                            st.markdown(f"**A:** {clickable_preview}", unsafe_allow_html=True)
                            st.markdown(f"*Sources used: {len(entry['source_ids'])}*")
                    
                    st.markdown("---")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #6c757d;">
        <small>
        © 2025 Benjamin Goldstein | AI-powered Daily Worker Search Database<br>
        Software licensed under MIT License | Newspaper content is in the public domain<br>
        Powered by sentence-transformers and Pinecone | Data sourced from Internet Archive
        </small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()