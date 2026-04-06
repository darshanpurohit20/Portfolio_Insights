import os
import smtplib
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_pdf_buffer(portfolio_items, summary_stats):
    """
    Generates a PDF using reportlab and returns a BytesIO buffer.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor('#2c3e50'))
    elements.append(Paragraph("Portfolio Insights Report", title_style))
    
    # Date
    date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=12, spaceAfter=20, textColor=colors.HexColor('#7f8c8d'))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y - %I:%M %p %Z')}", date_style))
    
    # Summary Table
    elements.append(Paragraph("Summary", styles['Heading2']))
    summary_data = [
        ["Total Invested", f"Rs. {summary_stats.get('totalInvested', 0):,.2f}"],
        ["Current Value", f"Rs. {summary_stats.get('totalValue', 0):,.2f}"],
        ["Total P&L", f"Rs. {summary_stats.get('totalPnl', 0):,.2f}"],
        ["P&L %", f"{summary_stats.get('totalPnlPercent', 0):.2f}%"]
    ]
    
    summary_table = Table(summary_data, colWidths=[150, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#212529')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Holdings Table
    elements.append(Paragraph("Holdings Breakdown", styles['Heading2']))
    
    table_data = [["Symbol", "Qty", "Buy Price", "LTP", "P&L", "P&L %"]]
    for item in portfolio_items:
        table_data.append([
            item.get('symbol', ''),
            str(item.get('qty', 0)),
            f"{item.get('buyPrice', 0):.2f}",
            f"{item.get('currentPrice', 0):.2f}",
            f"{item.get('pnl', 0):.2f}",
            f"{item.get('pnlPercent', 0):.2f}%"
        ])
        
    holdings_table = Table(table_data, colWidths=[120, 50, 80, 80, 100, 80])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffffff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e9ecef')),
    ])
    
    # Color code P&L
    for i, row in enumerate(portfolio_items):
        r_idx = i + 1
        pnl = row.get('pnl', 0)
        c = colors.HexColor('#dc3545') if pnl < 0 else colors.HexColor('#198754')
        style.add('TEXTCOLOR', (4, r_idx), (5, r_idx), c)
        
    holdings_table.setStyle(style)
    elements.append(holdings_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def send_portfolio_email(to_email, pdf_buffer):
    """
    Sends the generated PDF buffer via email.
    """
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_APP_PASSWORD")
    
    if not sender_email or not sender_password:
        logger.error("Email credentials not set. Skipping email dispatch.")
        return False

    msg = EmailMessage()
    msg['Subject'] = 'Your Scheduled Portfolio Insights Report'
    msg['From'] = sender_email
    msg['To'] = to_email
    msg.set_content("Please find attached your latest portfolio summary.")

    msg.add_attachment(
        pdf_buffer.read(), 
        maintype='application', 
        subtype='pdf', 
        filename='Portfolio_Report.pdf'
    )

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info(f"Report emailed successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
