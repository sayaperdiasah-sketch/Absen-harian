from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from datetime import datetime
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
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# ============ KONFIGURASI LOGIN ============
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'anakanakkesayanganbapak'

DATA_FILE = 'data_absen.json'

# ============ FUNGSI DATABASE ============
def init_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)

def load_data():
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        try:
            return json.load(f)
        except:
            return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
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
    return render_template('index.html')

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

# ============ API ABSEN ============
@app.route('/absen_masuk', methods=['POST'])
@limiter.limit("5 per minute")
def absen_masuk():
    nama = request.form.get('nama', '').strip()
    foto = request.form.get('foto', '')
    
    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    
    data = load_data()
    today = datetime.now().strftime("%d-%m-%Y")
    
    for item in data:
        if item.get('nama', '').lower() == nama.lower() and item.get('tanggal', '') == today and item.get('status') == 'Hadir':
            return jsonify({'status': 'error', 'message': f'{nama} sudah absen masuk hari ini!'})
    
    now = datetime.now()
    data_baru = {
        'id': str(int(datetime.now().timestamp())),
        'nama': nama,
        'tanggal': today,
        'jam_masuk': now.strftime("%H:%M:%S"),
        'jam_keluar': '-',
        'status': 'Hadir',
        'keterangan': '-',
        'foto_masuk': foto if foto else None,
        'foto_keluar': None
    }
    
    data.append(data_baru)
    save_data(data)
    
    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} berhasil absen masuk pada jam {now.strftime("%H:%M:%S")}'
    })

@app.route('/absen_keluar', methods=['POST'])
@limiter.limit("5 per minute")
def absen_keluar():
    nama = request.form.get('nama', '').strip()
    foto = request.form.get('foto', '')
    
    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    if not foto:
        return jsonify({'status': 'error', 'message': '📸 Harap ambil foto terlebih dahulu!'})
    
    data = load_data()
    today = datetime.now().strftime("%d-%m-%Y")
    found = False
    
    for item in data:
        if (item.get('nama', '').lower() == nama.lower() and 
            item.get('tanggal', '') == today and 
            item.get('status') == 'Hadir' and
            item.get('jam_keluar') == '-'):
            item['jam_keluar'] = datetime.now().strftime("%H:%M:%S")
            item['foto_keluar'] = foto
            found = True
            break
    
    if not found:
        return jsonify({
            'status': 'error', 
            'message': f'❌ {nama} belum absen masuk hari ini atau sudah absen keluar!'
        })
    
    save_data(data)
    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} berhasil absen keluar pada jam {datetime.now().strftime("%H:%M:%S")}'
    })

@app.route('/izin', methods=['POST'])
@limiter.limit("5 per minute")
def izin():
    nama = request.form.get('nama', '').strip()
    keterangan = request.form.get('keterangan', '').strip()
    foto = request.form.get('foto', '')
    
    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    if not keterangan:
        return jsonify({'status': 'error', 'message': '📝 Silakan isi keterangan!'})
    if not foto:
        return jsonify({'status': 'error', 'message': '📸 Harap ambil foto!'})https://absen-harian-production.up.railway.app/admin
    
    data = load_data()
    today = datetime.now().strftime("%d-%m-%Y")
    
    for item in data:
        if item.get('nama', '').lower() == nama.lower() and item.get('tanggal', '') == today and item.get('status') in ['Izin', 'Sakit', 'Dinas']:
            return jsonify({'status': 'error', 'message': f'{nama} sudah mengajukan {item.get("status")} hari ini!'})
    
    data_baru = {
        'id': str(int(datetime.now().timestamp())),
        'nama': nama,
        'tanggal': today,
        'jam_masuk': '-',
        'jam_keluar': '-',
        'status': 'Izin',
        'keterangan': keterangan,
        'foto_masuk': foto,
        'foto_keluar': None
    }
    
    data.append(data_baru)
    save_data(data)
    
    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} - Izin berhasil dicatat!'
    })

# ============ API ADMIN ============
@app.route('/api/data')
@login_required
@limiter.limit("30 per minute")
def api_get_data():
    data = load_data()
    for item in data:
        if 'foto_masuk' in item:
            item['foto_masuk'] = 'Ada' if item['foto_masuk'] and len(str(item['foto_masuk'])) > 100 else None
        if 'foto_keluar' in item:
            item['foto_keluar'] = 'Ada' if item['foto_keluar'] and len(str(item['foto_keluar'])) > 100 else None
    return jsonify(data)

@app.route('/api/data/full')
@login_required
@limiter.limit("30 per minute")
def api_get_data_full():
    try:
        data = load_data()
        for item in data:
            if 'id' not in item:
                item['id'] = str(int(datetime.now().timestamp()))
            if 'status' not in item:
                item['status'] = 'Hadir'
            if 'keterangan' not in item:
                item['keterangan'] = '-'
            if 'foto_masuk' not in item:
                item['foto_masuk'] = None
            if 'foto_keluar' not in item:
                item['foto_keluar'] = None
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/delete/<id>', methods=['DELETE'])
@login_required
@limiter.limit("10 per minute")
def api_delete_data(id):
    data = load_data()
    data = [d for d in data if d.get('id', '') != id]
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
    new_jam_masuk = request.json.get('jam_masuk')
    new_jam_keluar = request.json.get('jam_keluar')
    new_status = request.json.get('status')
    new_keterangan = request.json.get('keterangan')
    for item in data:
        if item.get('id', '') == id:
            if new_nama:
                item['nama'] = new_nama
            if new_jam_masuk:
                item['jam_masuk'] = new_jam_masuk
            if new_jam_keluar:
                item['jam_keluar'] = new_jam_keluar
            if new_status:
                item['status'] = new_status
            if new_keterangan is not None:
                item['keterangan'] = new_keterangan
            break
    save_data(data)
    return jsonify({'status': 'success', 'message': 'Data berhasil diupdate!'})

# ============ EXPORT PDF ============
@app.route('/api/export/pdf')
@login_required
@limiter.limit("10 per minute")
def export_pdf():
    data = load_data()
    if not data:
        return jsonify({'status': 'error', 'message': 'Tidak ada data untuk diexport!'})
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#2c3e50'), alignment=1, spaceAfter=30)
    elements.append(Paragraph("📋 LAPORAN REKAP ABSEN", title_style))
    date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#7f8c8d'), alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"Dicetak: {datetime.now().strftime('%d %B %Y %H:%M')}", date_style))
    table_data = [['No', 'Nama', 'Tanggal', 'Jam Masuk', 'Jam Keluar', 'Status', 'Keterangan']]
    for idx, item in enumerate(data, 1):
        table_data.append([
            str(idx),
            item.get('nama', '-'),
            item.get('tanggal', '-'),
            item.get('jam_masuk', '-'),
            item.get('jam_keluar', '-'),
            item.get('status', 'Hadir'),
            item.get('keterangan', '-')
        ])
    table = Table(table_data, colWidths=[0.4*inch, 1.2*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 1.5*inch])
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
    elements.append(Paragraph(f"Total Data: {len(data)} orang", footer_style))
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f'rekap_absen_{datetime.now().strftime("%Y%m%d")}.pdf', mimetype='application/pdf')

# ============ WAKTU ============
@app.route('/get_waktu')
@limiter.limit("30 per minute")
def get_waktu():
    now = datetime.now()
    return jsonify({'tanggal': now.strftime("%d %B %Y"), 'jam': now.strftime("%H:%M:%S")})

if __name__ == '__main__':
    init_data_file()
    app.run(debug=True, host='0.0.0.0', port=5000)
