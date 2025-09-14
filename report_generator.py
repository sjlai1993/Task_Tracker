
# report_generator.py

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import black, HexColor
from reportlab.lib.units import mm

class ReportGenerator:
    def __init__(self, output_path, name, designation, month_year):
        self.output_path = output_path
        self.name = name
        self.designation = designation
        self.month_year = month_year
        self.styles = getSampleStyleSheet()
        self.story = []

    def _header(self, canvas, doc):
        """Draws the header on each page."""
        canvas.saveState()
        width, height = doc.width, doc.height
        page_width, page_height = doc.pagesize

        # Company Name
        canvas.setFont('Helvetica-Bold', 14)
        canvas.drawString(20 * mm, page_height - 20 * mm, "T.Y.LIN INTERNATIONAL SDN BHD")

        # Form Number
        canvas.setFont('Helvetica', 11)
        canvas.drawRightString(page_width - 20 * mm, page_height - 20 * mm, "Form TYL/QA83")
        
        # Report Title
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawCentredString(page_width / 2, page_height - 28 * mm, "Project Manager / Engineers Monthly Design Record")
        canvas.line(page_width / 2 - 70*mm, page_height - 29 * mm, page_width / 2 + 70*mm, page_height - 29 * mm)

        # User Info
        canvas.setFont('Helvetica', 11)
        canvas.drawString(20 * mm, page_height - 40 * mm, f"Name: {self.name}")
        canvas.line(35*mm, page_height - 41*mm, 100*mm, page_height-41*mm)
        
        canvas.drawString(110 * mm, page_height - 40 * mm, f"Designation: {self.designation}")
        canvas.line(135*mm, page_height - 41*mm, 200*mm, page_height-41*mm)

        # Month & Year
        canvas.drawRightString(page_width - 20 * mm, page_height - 40 * mm, f"Month & Year: {self.month_year}")
        canvas.line(page_width - 58 * mm, page_height - 41 * mm, page_width - 20 * mm, page_height - 41 * mm)

        canvas.restoreState()

    def _footer(self):
        """Creates the footer flowable elements to be added ONLY at the end of the story."""
        footer_story = []
        
        styles = self.styles
        styleN = styles['Normal']
        styleN.fontName = 'Helvetica'
        styleN.fontSize = 10
        styleN.alignment = TA_LEFT
        
        styleB = styles['Normal']
        styleB.fontName = 'Helvetica-Bold'
        styleB.fontSize = 10

        p_review = Paragraph("<u>Overall Review by Principal/ Immediate Superior</u>", styleB)
        footer_story.append(p_review)
        footer_story.append(Spacer(1, 8 * mm))

        p_comment = Paragraph("Comment :", styleN)
        footer_story.append(p_comment)
        footer_story.append(Spacer(1, 10 * mm))
        
        p_recommend = Paragraph("Recommendation :", styleN)
        footer_story.append(p_recommend)
        footer_story.append(Spacer(1, 15 * mm))

        footer_table_data = [
            ['', 'Evaluated by :', '________________________', 'Date :', '________________________'],
        ]
        
        footer_table = Table(footer_table_data, colWidths=[60*mm, 30*mm, 60*mm, 15*mm, 40*mm])
        footer_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        
        footer_story.append(footer_table)
        return footer_story

    def generate_report(self, table_data, spans):
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=landscape(A4),
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=45 * mm,
            bottomMargin=15 * mm
        )

        main_table = Table(table_data, repeatRows=1)
        
        # Define Table Style
        style = TableStyle([
            # General Styles
            ('GRID', (0, 0), (-1, -1), 0.5, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            
            # Header Styles
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#E0E0E0')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data Styles
            # =====================================================================
            # === MODIFIED SECTION START (Align project code top-left) ===
            # =====================================================================
            ('ALIGN', (0, 1), (0, -1), 'LEFT'), # Job No
            ('VALIGN', (0, 1), (0, -1), 'TOP'),  # Job No
            # =====================================================================
            # === MODIFIED SECTION END ===
            # =====================================================================
            ('ALIGN', (3, 1), (7, -1), 'CENTER'), # % Weeks
            ('ALIGN', (8, 1), (9, -1), 'CENTER'), # Reviewed
            ('ALIGN', (10, 1), (11, -1), 'CENTER'), # Compliance
            ('LEFTPADDING', (2, 1), (2, -1), 4), # Description left padding
            ('VALIGN', (2,1), (2,-1), 'TOP'), # Description top align
        ])

        # Add all the dynamic spans
        for span_cmd in spans:
            style.add(*span_cmd)

        main_table.setStyle(style)
        
        self.story.append(main_table)
        self.story.extend(self._footer())

        doc.build(self.story, onFirstPage=self._header, onLaterPages=self._header)