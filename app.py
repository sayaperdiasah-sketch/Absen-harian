from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

DATA_FILE = 'data_absen.json'

def init_data_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)

def load_data():
    init_data_file()
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/absen_masuk', methods=['POST'])
def absen_masuk():
    nama = request.form.get('nama', '').strip()
    
    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    
    data = load_data()
    today = datetime.now().strftime("%d-%m-%Y")
    
    for item in data:
        if item['nama'].lower() == nama.lower() and item['tanggal'] == today:
            return jsonify({'status': 'error', 'message': f'{nama} sudah absen masuk hari ini!'})
    
    now = datetime.now()
    data_baru = {
        'nama': nama,
        'tanggal': today,
        'jam_masuk': now.strftime("%H:%M:%S"),
        'jam_keluar': '-'
    }
    
    data.append(data_baru)
    save_data(data)
    
    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} berhasil absen masuk pada jam {now.strftime("%H:%M:%S")}'
    })

@app.route('/absen_keluar', methods=['POST'])
def absen_keluar():
    nama = request.form.get('nama', '').strip()
    
    if not nama:
        return jsonify({'status': 'error', 'message': 'Nama tidak boleh kosong!'})
    
    data = load_data()
    today = datetime.now().strftime("%d-%m-%Y")
    found = False
    
    for item in data:
        if (item['nama'].lower() == nama.lower() and 
            item['tanggal'] == today and 
            item['jam_keluar'] == '-'):
            item['jam_keluar'] = datetime.now().strftime("%H:%M:%S")
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

@app.route('/get_data')
def get_data():
    data = load_data()
    return jsonify(data)

@app.route('/get_waktu')
def get_waktu():
    now = datetime.now()
    return jsonify({
        'tanggal': now.strftime("%d %B %Y"),
        'jam': now.strftime("%H:%M:%S")
    })

if __name__ == '__main__':
    init_data_file()
    app.run(debug=True, host='0.0.0.0', port=5000)
