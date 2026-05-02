from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime, date
import random

app = Flask(__name__)
app.secret_key = 'victoria_vicsion_secret_v3'

def db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        nombre TEXT,
        email TEXT,
        telefono TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT,
        email TEXT,
        tipo TEXT,
        estatus TEXT DEFAULT 'Nuevo',
        asesor TEXT,
        asesor_nombre TEXT,
        notas TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS jornadas (
        id INTEGER PRIMARY KEY,
        nombre TEXT,
        asesor TEXT,
        fase TEXT,
        activa INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY,
        cliente_id INTEGER,
        cliente_nombre TEXT,
        asesor TEXT,
        descripcion TEXT,
        monto REAL,
        estatus TEXT DEFAULT 'Pendiente',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Insertar usuarios por defecto
    c.execute("SELECT 1 FROM users WHERE username='admin'")
    if not c.fetchone():
        users = [
            ('admin',     '1234', 'admin',  'Victor Pérez',      'admin@victoriavicsion.com',    '0414-0000001'),
            ('asesor1',   '1234', 'asesor', 'Kayret Licet',      'kayret@victoriavicsion.com',   '0414-1234567'),
            ('asesor2',   '1234', 'asesor', 'Andreína Molina',   'andreina@victoriavicsion.com', '0424-2345678'),
            ('asesor3',   '1234', 'asesor', 'Luis Fermín',       'luis@victoriavicsion.com',     '0412-3456789'),
            ('asesor4',   '1234', 'asesor', 'Daniela Ríos',      'daniela@victoriavicsion.com',  '0426-4567890'),
        ]
        c.executemany("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(?,?,?,?,?,?)", users)

    # Insertar clientes de ejemplo
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        today = date.today().isoformat()
        estatuses = ['Nuevo', 'En seguimiento', 'Cerrado', 'Interesado', 'No interesado']
        tipos = ['Nuevo', 'Familiar / comparte número', 'Referido']
        sample_clients = [
            ('María',    'González',  '0414-1111111', 'maria@gmail.com',    tipos[0], estatuses[0], 'asesor1', 'Kayret Licet',    'Cliente interesada en jornada mensual', today),
            ('Pedro',    'Hernández', '0424-2222222', 'pedro@gmail.com',    tipos[2], estatuses[1], 'asesor1', 'Kayret Licet',    'Referido por González', today),
            ('Luisa',    'Martínez',  '0412-3333333', 'luisa@gmail.com',    tipos[1], estatuses[3], 'asesor2', 'Andreína Molina', 'Compartirá número con hermana', today),
            ('Carlos',   'Rodríguez', '0426-4444444', 'carlos@gmail.com',   tipos[0], estatuses[2], 'asesor2', 'Andreína Molina', 'Cerrado exitosamente', today),
            ('Ana',      'López',     '0414-5555555', 'ana@gmail.com',      tipos[2], estatuses[1], 'asesor3', 'Luis Fermín',     'Sigue interesada', today),
            ('José',     'Pérez',     '0424-6666666', 'jose@gmail.com',     tipos[0], estatuses[4], 'asesor3', 'Luis Fermín',     'No le convencieron los precios', today),
            ('Valentina','Díaz',      '0412-7777777', 'vale@gmail.com',     tipos[1], estatuses[0], 'asesor4', 'Daniela Ríos',   'Primera consulta hoy', today),
            ('Roberto',  'Sánchez',   '0416-8888888', 'roberto@gmail.com',  tipos[2], estatuses[3], 'asesor4', 'Daniela Ríos',   'Muy interesado, pendiente de fecha', today),
        ]
        c.executemany(
            "INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            sample_clients
        )

    # Insertar jornadas de ejemplo
    c.execute("SELECT COUNT(*) FROM jornadas")
    if c.fetchone()[0] == 0:
        fases = ['Captación', 'Prospección', 'Seguimiento', 'Cierre', 'Postventa']
        jornadas_data = [
            ('Jornada Matutina Abril',  'asesor1', random.choice(fases), 1),
            ('Jornada Tarde Mayo',      'asesor2', random.choice(fases), 1),
            ('Campaña Referidos',       'asesor3', random.choice(fases), 1),
            ('Jornada Premium Clientes','asesor4', random.choice(fases), 1),
            ('Evento Especial',         'asesor1', random.choice(fases), 1),
        ]
        c.executemany("INSERT INTO jornadas(nombre,asesor,fase,activa) VALUES(?,?,?,?)", jornadas_data)

    conn.commit()
    conn.close()

init_db()

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        conn = db()
        c = conn.cursor()
        c.execute('SELECT username, role, nombre FROM users WHERE username=? AND password=?',
                  (request.form['username'], request.form['password']))
        user = c.fetchone()
        conn.close()
        if user:
            session['user']   = user['username']
            session['role']   = user['role']
            session['nombre'] = user['nombre']
            return redirect('/dashboard')
        error = 'Credenciales incorrectas'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    conn = db()
    c = conn.cursor()
    today = date.today().isoformat()

    if session['role'] == 'admin':
        # Asesores y sus clientes del día
        c.execute("SELECT * FROM users WHERE role='asesor'")
        asesores = c.fetchall()
        asesores_data = []
        for a in asesores:
            c.execute("SELECT COUNT(*) as cnt FROM clients WHERE asesor=? AND date(created_at)=?", (a['username'], today))
            cnt = c.fetchone()['cnt']
            asesores_data.append({'asesor': a, 'clientes_hoy': cnt})

        # Jornadas activas
        c.execute("SELECT j.*, u.nombre as asesor_nombre FROM jornadas j LEFT JOIN users u ON j.asesor=u.username WHERE j.activa=1")
        jornadas = c.fetchall()

        conn.close()
        return render_template('dashboard_admin.html',
                               asesores_data=asesores_data,
                               jornadas=jornadas,
                               nombre=session['nombre'],
                               role=session['role'])
    else:
        # Vista asesor
        c.execute('SELECT * FROM clients WHERE asesor=? ORDER BY id DESC', (session['user'],))
        clients = c.fetchall()
        c.execute('SELECT COUNT(*) as cnt FROM clients WHERE asesor=? AND date(created_at)=?', (session['user'], today))
        hoy = c.fetchone()['cnt']
        conn.close()
        return render_template('dashboard_asesor.html',
                               clients=clients,
                               total=len(clients),
                               hoy=hoy,
                               nombre=session['nombre'],
                               role=session['role'])

# ─── CLIENTES ────────────────────────────────────────────────────────────────

@app.route('/clientes')
def clientes():
    if 'user' not in session:
        return redirect('/')
    conn = db()
    c = conn.cursor()

    search  = request.args.get('search', '')
    estatus = request.args.get('estatus', '')
    asesor  = request.args.get('asesor', '')

    query  = 'SELECT * FROM clients WHERE 1=1'
    params = []

    if session['role'] != 'admin':
        query += ' AND asesor=?'
        params.append(session['user'])

    if search:
        query += ' AND (nombre LIKE ? OR apellido LIKE ? OR telefono LIKE ?)'
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if estatus:
        query += ' AND estatus=?'
        params.append(estatus)
    if asesor and session['role'] == 'admin':
        query += ' AND asesor=?'
        params.append(asesor)

    query += ' ORDER BY id DESC'
    c.execute(query, params)
    clients = c.fetchall()

    asesores = []
    if session['role'] == 'admin':
        c.execute("SELECT username, nombre FROM users WHERE role='asesor'")
        asesores = c.fetchall()

    conn.close()
    return render_template('clientes.html', clients=clients, asesores=asesores,
                           search=search, estatus_filter=estatus, asesor_filter=asesor,
                           nombre=session['nombre'], role=session['role'])

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if 'user' not in session:
        return redirect('/')
    if request.method == 'POST':
        conn = db()
        c = conn.cursor()
        c.execute("SELECT nombre FROM users WHERE username=?", (session['user'],))
        asesor_nom = c.fetchone()['nombre']
        c.execute('''INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas)
                     VALUES(?,?,?,?,?,?,?,?,?)''',
                  (request.form['nombre'], request.form['apellido'], request.form['telefono'],
                   request.form.get('email',''), request.form['tipo'], request.form.get('estatus','Nuevo'),
                   session['user'], asesor_nom, request.form.get('notas','')))
        conn.commit()
        conn.close()
        return redirect('/clientes')
    return render_template('cliente_form.html', client=None, nombre=session['nombre'], role=session['role'])

@app.route('/clientes/editar/<int:cid>', methods=['GET', 'POST'])
def editar_cliente(cid):
    if 'user' not in session:
        return redirect('/')
    conn = db()
    c = conn.cursor()

    if session['role'] != 'admin':
        c.execute('SELECT * FROM clients WHERE id=? AND asesor=?', (cid, session['user']))
    else:
        c.execute('SELECT * FROM clients WHERE id=?', (cid,))

    client = c.fetchone()
    if not client:
        conn.close()
        return redirect('/clientes')

    if request.method == 'POST':
        c.execute('''UPDATE clients SET nombre=?,apellido=?,telefono=?,email=?,tipo=?,estatus=?,notas=?
                     WHERE id=?''',
                  (request.form['nombre'], request.form['apellido'], request.form['telefono'],
                   request.form.get('email',''), request.form['tipo'], request.form['estatus'],
                   request.form.get('notas',''), cid))
        conn.commit()
        conn.close()
        return redirect('/clientes')

    conn.close()
    return render_template('cliente_form.html', client=client, nombre=session['nombre'], role=session['role'])

@app.route('/clientes/eliminar/<int:cid>', methods=['POST'])
def eliminar_cliente(cid):
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM clients WHERE id=?', (cid,))
    conn.commit()
    conn.close()
    return redirect('/clientes')

# ─── USUARIOS (solo admin) ───────────────────────────────────────────────────

@app.route('/usuarios')
def usuarios():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY role, nombre')
    users = c.fetchall()
    conn.close()
    return render_template('usuarios.html', users=users, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/nuevo', methods=['GET', 'POST'])
def nuevo_usuario():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    error = None
    if request.method == 'POST':
        conn = db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(?,?,?,?,?,?)",
                      (request.form['username'], request.form['password'], request.form['role'],
                       request.form['nombre'], request.form.get('email',''), request.form.get('telefono','')))
            conn.commit()
            conn.close()
            return redirect('/usuarios')
        except sqlite3.IntegrityError:
            error = 'El nombre de usuario ya existe.'
            conn.close()
    return render_template('usuario_form.html', user=None, error=error, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/editar/<int:uid>', methods=['GET', 'POST'])
def editar_usuario(uid):
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id=?', (uid,))
    user = c.fetchone()
    if not user:
        conn.close()
        return redirect('/usuarios')
    error = None
    if request.method == 'POST':
        new_pass = request.form.get('password','').strip()
        if new_pass:
            c.execute('UPDATE users SET nombre=?,role=?,email=?,telefono=?,password=? WHERE id=?',
                      (request.form['nombre'], request.form['role'],
                       request.form.get('email',''), request.form.get('telefono',''), new_pass, uid))
        else:
            c.execute('UPDATE users SET nombre=?,role=?,email=?,telefono=? WHERE id=?',
                      (request.form['nombre'], request.form['role'],
                       request.form.get('email',''), request.form.get('telefono',''), uid))
        conn.commit()
        conn.close()
        return redirect('/usuarios')
    conn.close()
    return render_template('usuario_form.html', user=user, error=error, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/eliminar/<int:uid>', methods=['POST'])
def eliminar_usuario(uid):
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id=? AND username != "admin"', (uid,))
    conn.commit()
    conn.close()
    return redirect('/usuarios')

# ─── FACTURACIÓN ─────────────────────────────────────────────────────────────

@app.route('/facturacion')
def facturacion():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM facturas ORDER BY id DESC')
    facturas = c.fetchall()
    c.execute('SELECT SUM(monto) as total FROM facturas WHERE estatus="Pagado"')
    total_pagado = c.fetchone()['total'] or 0
    c.execute('SELECT * FROM clients ORDER BY nombre')
    clients = c.fetchall()
    conn.close()
    return render_template('facturacion.html', facturas=facturas, total_pagado=total_pagado,
                           clients=clients, nombre=session['nombre'], role=session['role'])

@app.route('/facturacion/nueva', methods=['POST'])
def nueva_factura():
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    cliente_id = request.form['cliente_id']
    c.execute('SELECT nombre, apellido FROM clients WHERE id=?', (cliente_id,))
    cl = c.fetchone()
    cliente_nombre = f"{cl['nombre']} {cl['apellido']}" if cl else 'Desconocido'
    c.execute('''INSERT INTO facturas(cliente_id,cliente_nombre,asesor,descripcion,monto,estatus)
                 VALUES(?,?,?,?,?,?)''',
              (cliente_id, cliente_nombre, session['user'],
               request.form['descripcion'], float(request.form['monto']),
               request.form.get('estatus','Pendiente')))
    conn.commit()
    conn.close()
    return redirect('/facturacion')

@app.route('/facturacion/estatus/<int:fid>', methods=['POST'])
def cambiar_estatus_factura(fid):
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('UPDATE facturas SET estatus=? WHERE id=?', (request.form['estatus'], fid))
    conn.commit()
    conn.close()
    return redirect('/facturacion')

@app.route('/facturacion/eliminar/<int:fid>', methods=['POST'])
def eliminar_factura(fid):
    if 'user' not in session or session['role'] != 'admin':
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('DELETE FROM facturas WHERE id=?', (fid,))
    conn.commit()
    conn.close()
    return redirect('/facturacion')

# ─── PERFIL ───────────────────────────────────────────────────────────────────

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'user' not in session:
        return redirect('/')
    conn = db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?', (session['user'],))
    user = c.fetchone()
    if request.method == 'POST':
        new_pass = request.form.get('password','').strip()
        if new_pass:
            c.execute('UPDATE users SET nombre=?,email=?,telefono=?,password=? WHERE username=?',
                      (request.form['nombre'], request.form.get('email',''),
                       request.form.get('telefono',''), new_pass, session['user']))
        else:
            c.execute('UPDATE users SET nombre=?,email=?,telefono=? WHERE username=?',
                      (request.form['nombre'], request.form.get('email',''),
                       request.form.get('telefono',''), session['user']))
        conn.commit()
        session['nombre'] = request.form['nombre']
        conn.close()
        return redirect('/dashboard')
    conn.close()
    return render_template('perfil.html', user=user, nombre=session['nombre'], role=session['role'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
