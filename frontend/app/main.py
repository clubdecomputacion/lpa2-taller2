from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT
from xml.sax.saxutils import escape
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'lpa2-taller2-dev')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')

COLOR_PRIMARIO = colors.HexColor('#2E7D32')
COLOR_FONDO = colors.HexColor('#F1F8E9')


def formato_moneda(valor):
    """Formatea un número como moneda: 1234.5 -> $ 1,234.50"""
    return f"$ {valor:,.2f}"


def texto(valor):
    """Escapa el texto para Paragraph y respeta los saltos de línea."""
    return escape(str(valor)).replace('\n', '<br/>')


def bloque_datos(titulo, datos, estilos):
    """Crea el bloque de información de la empresa o del cliente."""
    lineas = [f"<b>{titulo}</b>", f"<b>{texto(datos.get('nombre', ''))}</b>"]
    if datos.get('direccion'):
        lineas.append(texto(datos['direccion']))
    if datos.get('telefono'):
        lineas.append(f"Tel: {texto(datos['telefono'])}")
    if datos.get('email'):
        lineas.append(f"Email: {texto(datos['email'])}")
    return Paragraph('<br/>'.join(lineas), estilos['Normal'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    id_factura = request.form.get('id_factura', '').strip()
    if not id_factura:
        flash("Debe ingresar un ID de factura")
        return redirect(url_for('index'))

    try:
        response = requests.get(f'{BACKEND_URL}/facturas/v1/{id_factura}', timeout=10)

        if response.status_code != 200:
            flash(f"Factura '{id_factura}' no encontrada")
            return redirect(url_for('index'))

        factura = response.json()

        # Crear buffer y doc para la creación del PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            title=f"Factura {factura['numero_factura']}",
        )
        estilos = getSampleStyleSheet()
        estilo_titulo = ParagraphStyle(
            'TituloFactura', parent=estilos['Title'], textColor=COLOR_PRIMARIO
        )
        estilo_derecha = ParagraphStyle(
            'Derecha', parent=estilos['Normal'], alignment=TA_RIGHT
        )
        elements = []

        # Adicionar el Título, ID
        elements.append(Paragraph("FACTURA", estilo_titulo))
        elements.append(Paragraph(
            f"<b>N.º:</b> {texto(factura['numero_factura'])}<br/>"
            f"<b>Fecha de emisión:</b> {texto(factura['fecha_emision'])}",
            estilo_derecha,
        ))
        elements.append(Spacer(1, 10 * mm))

        # Agregar Información de la Empresa
        empresa = bloque_datos("EMISOR", factura['empresa'], estilos)

        # Agregar Información del Cliente
        cliente = bloque_datos("CLIENTE", factura['cliente'], estilos)

        tabla_partes = Table([[empresa, cliente]], colWidths=[85 * mm, 85 * mm])
        tabla_partes.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_FONDO),
            ('BOX', (0, 0), (0, 0), 0.5, COLOR_PRIMARIO),
            ('BOX', (1, 0), (1, 0), 0.5, COLOR_PRIMARIO),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(tabla_partes)
        elements.append(Spacer(1, 10 * mm))

        # Adicionar el Detalle de la Factura: cantidad, descripción, precio unitario y total
        filas = [["Cantidad", "Descripción", "Precio Unitario", "Total"]]
        for item in factura['detalle']:
            filas.append([
                str(item['cantidad']),
                Paragraph(texto(item['descripcion']), estilos['Normal']),
                formato_moneda(item['precio_unitario']),
                formato_moneda(item['total']),
            ])

        # Adicionar Subtotal, impuesto y Total
        inicio_totales = len(filas)
        filas.append(["", "", "Subtotal", formato_moneda(factura['subtotal'])])
        filas.append(["", "", "Impuesto (IVA)", formato_moneda(factura['impuesto'])])
        filas.append(["", "", "TOTAL", formato_moneda(factura['total'])])

        tabla_detalle = Table(
            filas,
            colWidths=[22 * mm, 78 * mm, 35 * mm, 35 * mm],
            repeatRows=1,
        )
        tabla_detalle.setStyle(TableStyle([
            # Encabezado
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_PRIMARIO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            # Ítems
            ('GRID', (0, 0), (-1, inicio_totales - 1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, inicio_totales - 1), [colors.white, COLOR_FONDO]),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Totales
            ('FONTNAME', (2, inicio_totales), (2, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (2, inicio_totales), (-1, inicio_totales), 0.5, colors.grey),
            ('BACKGROUND', (2, -1), (-1, -1), COLOR_PRIMARIO),
            ('TEXTCOLOR', (2, -1), (-1, -1), colors.white),
            ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(tabla_detalle)
        elements.append(Spacer(1, 15 * mm))
        elements.append(Paragraph("<i>Gracias por su compra.</i>", estilos['Normal']))

        # Generar el doc y limpiar el buffer
        doc.build(elements)
        buffer.seek(0)

        # Retornar a la página el PDF para visualizar y descargar
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=request.form.get('descargar') == '1',
            download_name=f"factura_{factura['numero_factura']}.pdf",
        )

    except requests.exceptions.ConnectionError:
        flash("Error de conexión con el servidor")
        return redirect(url_for('index'))
    except requests.exceptions.Timeout:
        flash("El servidor tardó demasiado en responder")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error al generar la factura: {e}")
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=os.getenv('DEBUG', 'false').lower() == 'true')
