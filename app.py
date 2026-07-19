@app.route('/absen_masuk', methods=['POST'])
def absen_masuk():
    nama = request.form.get('nama', '').strip()
    foto = request.form.get('foto', '')  # <-- TAMBAHKAN INI
    
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
        'foto_masuk': foto if foto else None,  # <-- SIMPAN FOTO
        'foto_keluar': None
    }
    
    data.append(data_baru)
    save_data(data)
    
    return jsonify({
        'status': 'success',
        'message': f'✅ {nama} berhasil absen masuk pada jam {now.strftime("%H:%M:%S")}'
    })
