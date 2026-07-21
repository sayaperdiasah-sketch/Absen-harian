from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

app = Flask(__name__)
app.secret_key = 'rahasia_admin_absen_12345'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ============ RATE LIMITING ============
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# ============ KONFIGURASI LOGIN ============
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'anakanakkesayanganbapak'

DATA_FILE = 'data_absen.json'
AGENDA_FILE = 'agenda.json'

# ============ ZONA WAKTU (WIB) ============
WIB = ZoneInfo("Asia/Jakarta")

def now_wib():
    return datetime.now(WIB)

# ============ FUNGSI DATABASE ============
def init_files():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(AGENDA_FILE):
        with open(AGENDA_FILE, 'w') as f:
            json.dump([], f)

def load_data():
    init_files()
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_agenda():
    init_files()
    with open(AGENDA_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_agenda(data):
    with open(AGENDA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ============ DEKORATOR LOGIN ============
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ ROUTE HALAMAN ============
@app.route('/')
@limiter.limit("30 per minute")
def index():
    # Ambil agenda aktif hari ini
    today = now_wib().strftime("%d-%m-%Y")
    agendas = load_agenda()
    active_agenda = None
    for a in agendas:
        if a.get('tanggal') == today and a.get('status') == 'active':
            active_agenda = a
            break
    return render_template('index.html', agenda=active_agenda)

@app.route('/admin')
@login_required
@limiter.limit("20 per minute")
def admin():
    return render_template('admin.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Username atau password salah!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============ API AGENDA (Admin) ============
@app.route('/api/agenda', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per minute")
def api_agenda():
    if request.method == 'POST':
        judul = request.form.get('judul', '').strip()
        deskripsi = request.form.get('deskripsi', '').strip()
        tanggal = request.form.get('tanggal', '').strip()
        if not judul or not tanggal:
            return jsonify({'status': 'error', 'message': 'Judul dan tanggal wajib diisi!'})
        # Cek apakah sudah ada agenda aktif di tanggal itu
        agendas = load_agenda()
        for a in agendas:
            if a.get('tanggal') == tanggal and a.get('status') == 'active':
                return jsonify({'status': 'error', 'message': f'Agenda aktif sudah ada untuk tanggal {tanggal}'})
        new_agenda = {
            'id': str(int(now_wib().timestamp())),
            'judul': judul,
            'deskripsi': deskripsi,
            'tanggal': tanggal,
            'status': 'active'
        }
        agendas.append(new_agenda)
        save_agenda(agendas)
        return jsonify({'status': 'success', 'message': 'Agenda berhasil dibuat!'})
    else:
        # GET: ambil semua agenda
        return jsonify(load_agenda())

@app.route('/api/agenda/complete/<id>', methods=['PUT'])
@login_required
@limiter.limit("10 per minute")
def complete_agenda(id):
    agendas = load_agenda()
    for a in agendas:
        if a.get('id') == id:
            a['status'] = 'completed'
            break
    save_agenda(agendas)
    return jsonify({'status': 'success', 'message': 'Agenda ditandai selesai!'})

# ============ API ABSEN (dengan agenda) ============
@app.route('/absen_masuk', methods=['POST'])
@limiter.limit("5 per minute")
def absen_masuk():
    nama = request.form.get('nama', '').strip()
    foto = request.form.get('foto', '')
    agenda_id = request.form.get('agenda_id', '')
    kategori = request.form.get('kategori', 'Hadir')
    keterangan = request.form.get('keterangan', '').strip()

    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    if not agenda_id:
        return jsonify({'status': 'error', 'message': 'Tidak ada agenda aktif hari ini!'})

    data = load_data()
    today = now_wib().strftime("%d-%m-%Y")

    # Cek apakah user sudah absen untuk agenda ini
    for item in data:
        if item.get('nama', '').lower() == nama.lower() and item.get('agenda_id') == agenda_id:
            return jsonify({'status': 'error', 'message': f'{nama} sudah absen untuk agenda ini!'})

    now = now_wib()
    data_baru = {
        'id': str(int(now.timestamp())),
        'nama': nama,
        'tanggal': today,
        'agenda_id': agenda_id,
        'kategori': kategori,
        'keterangan': keterangan if keterangan else '-',
        'jam': now.strftime("%H:%M:%S"),
        'foto': foto if foto else None
    }

    data.append(data_baru)
    save_data(data)

    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} - {kategori} berhasil dicatat pada {now.strftime("%H:%M:%S")}'
    })

# ============ API ADMIN (data absen per agenda) ============
@app.route('/api/data/full')
@login_required
@limiter.limit("30 per minute")
def api_get_data_full():
    try:
        data = load_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/delete/<id>', methods=['DELETE'])
@login_required
@limiter.limit("10 per minute")
def api_delete_data(id):
    data = load_data()
    data = [d for d in data if d.get('id') != id]
    save_data(data)
    return jsonify({'status': 'success', 'message': 'Data berhasil dihapus!'})

@app.route('/api/data/delete_all', methods=['DELETE'])
@login_required
@limiter.limit("5 per minute")
def api_delete_all():
    save_data([])
    return jsonify({'status': 'success', 'message': 'Semua data berhasil dihapus!'})

@app.route('/api/data/update/<id>', methods=['PUT'])
@login_required
@limiter.limit("10 per minute")
def api_update_data(id):
    data = load_data()
    new_nama = request.json.get('nama')
    new_kategori = request.json.get('kategori')
    new_keterangan = request.json.get('keterangan')
    for item in data:
        if item.get('id') == id:
            if new_nama:
                item['nama'] = new_nama
            if new_kategori:
                item['kategori'] = new_kategori
            if new_keterangan is not None:
                item['keterangan'] = new_keterangan
            break
    save_data(data)
    return jsonify({'status': 'success', 'message': 'Data berhasil diupdate!'})

# ============ EXPORT PDF ============
@app.route('/api/export/pdf/<agenda_id>')
@login_required
@limiter.limit("10 per minute")
def export_pdf(agenda_id):
    data = load_data()
    filtered = [d for d in data if d.get('agenda_id') == agenda_id]
    if not filtered:
        return jsonify({'status': 'error', 'message': 'Tidak ada data untuk agenda ini!'})
    # Ambil judul agenda
    agendas = load_agenda()
    judul_agenda = 'Agenda'
    for a in agendas:
        if a.get('id') == agenda_id:
            judul_agenda = a.get('judul', 'Agenda')
            break

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#2c3e50'), alignment=1, spaceAfter=30)
    elements.append(Paragraph(f"📋 LAPORAN LOGBOOK - {judul_agenda}", title_style))
    date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#7f8c8d'), alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"Dicetak: {now_wib().strftime('%d %B %Y %H:%M')}", date_style))
    table_data = [['No', 'Nama', 'Kategori', 'Keterangan', 'Jam']]
    for idx, item in enumerate(filtered, 1):
        table_data.append([
            str(idx),
            item.get('nama', '-'),
            item.get('kategori', '-'),
            item.get('keterangan', '-'),
            item.get('jam', '-')
        ])
    table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 2*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(table)
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#95a5a6'), alignment=1, spaceBefore=20)
    elements.append(Paragraph(f"Total: {len(filtered)} orang", footer_style))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'logbook_{agenda_id}.pdf', mimetype='application/pdf')

# ============ WAKTU ============
@app.route('/get_waktu')
@limiter.limit("30 per minute")
def get_waktu():
    now = now_wib()
    return jsonify({'tanggal': now.strftime("%d %B %Y"), 'jam': now.strftime("%H:%M:%S")})

if __name__ == '__main__':
    init_files()
    app.run(debug=True, host='0.0.0.0', port=5000)
