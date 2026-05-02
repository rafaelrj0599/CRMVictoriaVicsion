from flask import Flask, render_template, request, redirect, session
from datetime import date
import random
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'victoria_vicsion_secret_v3')

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2

    def db():
        return psycopg2.connect(DATABASE_URL)

    def fetchone(cursor):
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in cursor.description]
        return dict(zip(cols, row))

    def fetchall(cursor):
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in rows]

    PH = '%s'
else:
    import sqlite3

    def db():
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        return conn

    def fetchone(cursor):
        return cursor.fetchone()

    def fetchall(cursor):
        return cursor.fetchall()

    PH = '?'


def q(sql):
    return sql.replace('?', PH)


def init_db():
    conn = db()
    c = conn.cursor()

    if DATABASE_URL:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT,
            role TEXT, nombre TEXT, email TEXT, telefono TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY, nombre TEXT, apellido TEXT, telefono TEXT,
            email TEXT, tipo TEXT, estatus TEXT DEFAULT 'Nuevo',
            asesor TEXT, asesor_nombre TEXT, notas TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS jornadas (
            id SERIAL PRIMARY KEY, nombre TEXT, asesor TEXT, fase TEXT,
            activa INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS facturas (
            id SERIAL PRIMARY KEY, cliente_id INTEGER, cliente_nombre TEXT,
            asesor TEXT, descripcion TEXT, monto REAL, estatus TEXT DEFAULT 'Pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT,
            role TEXT, nombre TEXT, email TEXT, telefono TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY, nombre TEXT, apellido TEXT, telefono TEXT,
            email TEXT, tipo TEXT, estatus TEXT DEFAULT 'Nuevo',
            asesor TEXT, asesor_nombre TEXT, notas TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS jornadas (
            id INTEGER PRIMARY KEY, nombre TEXT, asesor TEXT, fase TEXT,
            activa INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY, cliente_id INTEGER, cliente_nombre TEXT,
            asesor TEXT, descripcion TEXT, monto REAL, estatus TEXT DEFAULT 'Pendiente',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')

    c.execute(q("SELECT 1 FROM users WHERE username='admin'"))
    if not fetchone(c):
        for u in [
            ('admin',   '1234', 'admin',  'Victor Perez',    'admin@victoriavicsion.com',    '0414-0000001'),
            ('asesor1', '1234', 'asesor', 'Kayret Licet',    'kayret@victoriavicsion.com',   '0414-1234567'),
            ('asesor2', '1234', 'asesor', 'Andreina Molina', 'andreina@victoriavicsion.com', '0424-2345678'),
            ('asesor3', '1234', 'asesor', 'Luis Fermin',     'luis@victoriavicsion.com',     '0412-3456789'),
            ('asesor4', '1234', 'asesor', 'Daniela Rios',    'daniela@victoriavicsion.com',  '0426-4567890'),
        ]:
            c.execute(q("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(?,?,?,?,?,?)"), u)

    c.execute("SELECT COUNT(*) FROM clients")
    row = c.fetchone()
    if (row[0] if isinstance(row, tuple) else row['count']) == 0:
        today = date.today().isoformat()
        for cl in [
            ('Maria','Gonzalez','0414-1111111','maria@gmail.com','Nuevo','Nuevo','asesor1','Kayret Licet','Interesada en jornada',today),
            ('Pedro','Hernandez','0424-2222222','pedro@gmail.com','Referido','En seguimiento','asesor1','Kayret Licet','Referido por Gonzalez',today),
            ('Luisa','Martinez','0412-3333333','luisa@gmail.com','Familiar / comparte numero','Interesado','asesor2','Andreina Molina','Comparte numero',today),
            ('Carlos','Rodriguez','0426-4444444','carlos@gmail.com','Nuevo','Cerrado','asesor2','Andreina Molina','Cerrado exitosamente',today),
            ('Ana','Lopez','0414-5555555','ana@gmail.com','Referido','En seguimiento','asesor3','Luis Fermin','Sigue interesada',today),
            ('Jose','Perez','0424-6666666','jose@gmail.com','Nuevo','No interesado','asesor3','Luis Fermin','No le convencieron precios',today),
            ('Valentina','Diaz','0412-7777777','vale@gmail.com','Familiar / comparte numero','Nuevo','asesor4','Daniela Rios','Primera consulta',today),
            ('Roberto','Sanchez','0416-8888888','roberto@gmail.com','Referido','Interesado','asesor4','Daniela Rios','Pendiente de fecha',today),
        ]:
            c.execute(q('''INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas,created_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?)'''), cl)

    c.execute("SELECT COUNT(*) FROM jornadas")
    row = c.fetchone()
    if (row[0] if isinstance(row, tuple) else row['count']) == 0:
        fases = ['Captacion','Prospeccion','Seguimiento','Cierre','Postventa']
        for j in [
            ('Jornada Matutina Abril','asesor1',random.choice(fases),1),
            ('Jornada Tarde Mayo','asesor2',random.choice(fases),1),
            ('Campana Referidos','asesor3',random.choice(fases),1),
            ('Jornada Premium','asesor4',random.choice(fases),1),
            ('Evento Especial','asesor1',random.choice(fases),1),
        ]:
            c.execute(q("INSERT INTO jornadas(nombre,asesor,fase,activa) VALUES(?,?,?,?)"), j)

    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        conn = db(); c = conn.cursor()
        c.execute(q('SELECT username,role,nombre FROM users WHERE username=? AND password=?'),
                  (request.form['username'], request.form['password']))
        user = fetchone(c); conn.close()
        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            session['nombre'] = user['nombre']
            return redirect('/dashboard')
        error = 'Credenciales incorrectas'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    conn = db(); c = conn.cursor()
    today = date.today().isoformat()
    if session['role'] == 'admin':
        c.execute(q("SELECT * FROM users WHERE role='asesor'")); asesores = fetchall(c)
        asesores_data = []
        for a in asesores:
            c.execute(q("SELECT COUNT(*) as cnt FROM clients WHERE asesor=? AND DATE(created_at)=?"), (a['username'], today))
            row = c.fetchone()
            cnt = row[0] if isinstance(row, tuple) else row['cnt']
            asesores_data.append({'asesor': a, 'clientes_hoy': cnt})
        c.execute("SELECT j.*, u.nombre as asesor_nombre FROM jornadas j LEFT JOIN users u ON j.asesor=u.username WHERE j.activa=1")
        jornadas = fetchall(c); conn.close()
        return render_template('dashboard_admin.html', asesores_data=asesores_data,
                               jornadas=jornadas, nombre=session['nombre'], role=session['role'])
    else:
        c.execute(q('SELECT * FROM clients WHERE asesor=? ORDER BY id DESC'), (session['user'],)); clients = fetchall(c)
        c.execute(q("SELECT COUNT(*) as cnt FROM clients WHERE asesor=? AND DATE(created_at)=?"), (session['user'], today))
        row = c.fetchone(); hoy = row[0] if isinstance(row, tuple) else row['cnt']
        conn.close()
        return render_template('dashboard_asesor.html', clients=clients, total=len(clients),
                               hoy=hoy, nombre=session['nombre'], role=session['role'])

@app.route('/clientes')
def clientes():
    if 'user' not in session: return redirect('/')
    conn = db(); c = conn.cursor()
    search = request.args.get('search',''); estatus = request.args.get('estatus',''); asesor = request.args.get('asesor','')
    query = 'SELECT * FROM clients WHERE 1=1'; params = []
    if session['role'] != 'admin':
        query += q(' AND asesor=?'); params.append(session['user'])
    if search:
        query += q(' AND (nombre LIKE ? OR apellido LIKE ? OR telefono LIKE ?)')
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if estatus:
        query += q(' AND estatus=?'); params.append(estatus)
    if asesor and session['role'] == 'admin':
        query += q(' AND asesor=?'); params.append(asesor)
    query += ' ORDER BY id DESC'
    c.execute(query, params); clients = fetchall(c)
    asesores = []
    if session['role'] == 'admin':
        c.execute(q("SELECT username,nombre FROM users WHERE role='asesor'")); asesores = fetchall(c)
    conn.close()
    return render_template('clientes.html', clients=clients, asesores=asesores,
                           search=search, estatus_filter=estatus, asesor_filter=asesor,
                           nombre=session['nombre'], role=session['role'])

@app.route('/clientes/nuevo', methods=['GET','POST'])
def nuevo_cliente():
    if 'user' not in session: return redirect('/')
    if request.method == 'POST':
        conn = db(); c = conn.cursor()
        c.execute(q("SELECT nombre FROM users WHERE username=?"), (session['user'],))
        row = fetchone(c); asesor_nom = row['nombre'] if row else session['user']
        c.execute(q('''INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas)
                       VALUES(?,?,?,?,?,?,?,?,?)'''),
                  (request.form['nombre'], request.form['apellido'], request.form['telefono'],
                   request.form.get('email',''), request.form['tipo'], request.form.get('estatus','Nuevo'),
                   session['user'], asesor_nom, request.form.get('notas','')))
        conn.commit(); conn.close(); return redirect('/clientes')
    return render_template('cliente_form.html', client=None, nombre=session['nombre'], role=session['role'])

@app.route('/clientes/editar/<int:cid>', methods=['GET','POST'])
def editar_cliente(cid):
    if 'user' not in session: return redirect('/')
    conn = db(); c = conn.cursor()
    if session['role'] != 'admin':
        c.execute(q('SELECT * FROM clients WHERE id=? AND asesor=?'), (cid, session['user']))
    else:
        c.execute(q('SELECT * FROM clients WHERE id=?'), (cid,))
    client = fetchone(c)
    if not client: conn.close(); return redirect('/clientes')
    if request.method == 'POST':
        c.execute(q('''UPDATE clients SET nombre=?,apellido=?,telefono=?,email=?,tipo=?,estatus=?,notas=? WHERE id=?'''),
                  (request.form['nombre'], request.form['apellido'], request.form['telefono'],
                   request.form.get('email',''), request.form['tipo'], request.form['estatus'],
                   request.form.get('notas',''), cid))
        conn.commit(); conn.close(); return redirect('/clientes')
    conn.close()
    return render_template('cliente_form.html', client=client, nombre=session['nombre'], role=session['role'])

@app.route('/clientes/eliminar/<int:cid>', methods=['POST'])
def eliminar_cliente(cid):
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q('DELETE FROM clients WHERE id=?'), (cid,)); conn.commit(); conn.close()
    return redirect('/clientes')

@app.route('/usuarios')
def usuarios():
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute('SELECT * FROM users ORDER BY role, nombre'); users = fetchall(c); conn.close()
    return render_template('usuarios.html', users=users, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/nuevo', methods=['GET','POST'])
def nuevo_usuario():
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    error = None
    if request.method == 'POST':
        conn = db(); c = conn.cursor()
        try:
            c.execute(q("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(?,?,?,?,?,?)"),
                      (request.form['username'], request.form['password'], request.form['role'],
                       request.form['nombre'], request.form.get('email',''), request.form.get('telefono','')))
            conn.commit(); conn.close(); return redirect('/usuarios')
        except Exception:
            error = 'El nombre de usuario ya existe.'; conn.close()
    return render_template('usuario_form.html', user=None, error=error, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/editar/<int:uid>', methods=['GET','POST'])
def editar_usuario(uid):
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q('SELECT * FROM users WHERE id=?'), (uid,)); user = fetchone(c)
    if not user: conn.close(); return redirect('/usuarios')
    error = None
    if request.method == 'POST':
        new_pass = request.form.get('password','').strip()
        if new_pass:
            c.execute(q('UPDATE users SET nombre=?,role=?,email=?,telefono=?,password=? WHERE id=?'),
                      (request.form['nombre'], request.form['role'],
                       request.form.get('email',''), request.form.get('telefono',''), new_pass, uid))
        else:
            c.execute(q('UPDATE users SET nombre=?,role=?,email=?,telefono=? WHERE id=?'),
                      (request.form['nombre'], request.form['role'],
                       request.form.get('email',''), request.form.get('telefono',''), uid))
        conn.commit(); conn.close(); return redirect('/usuarios')
    conn.close()
    return render_template('usuario_form.html', user=user, error=error, nombre=session['nombre'], role=session['role'])

@app.route('/usuarios/eliminar/<int:uid>', methods=['POST'])
def eliminar_usuario(uid):
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q("DELETE FROM users WHERE id=? AND username != 'admin'"), (uid,)); conn.commit(); conn.close()
    return redirect('/usuarios')

@app.route('/facturacion')
def facturacion():
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute('SELECT * FROM facturas ORDER BY id DESC'); facturas = fetchall(c)
    c.execute(q("SELECT SUM(monto) as total FROM facturas WHERE estatus='Pagado'")); row = fetchone(c)
    total_pagado = row['total'] if row and row['total'] else 0
    c.execute('SELECT * FROM clients ORDER BY nombre'); clients = fetchall(c); conn.close()
    return render_template('facturacion.html', facturas=facturas, total_pagado=total_pagado,
                           clients=clients, nombre=session['nombre'], role=session['role'])

@app.route('/facturacion/nueva', methods=['POST'])
def nueva_factura():
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    cliente_id = request.form['cliente_id']
    c.execute(q('SELECT nombre,apellido FROM clients WHERE id=?'), (cliente_id,)); cl = fetchone(c)
    cliente_nombre = f"{cl['nombre']} {cl['apellido']}" if cl else 'Desconocido'
    c.execute(q('''INSERT INTO facturas(cliente_id,cliente_nombre,asesor,descripcion,monto,estatus)
                   VALUES(?,?,?,?,?,?)'''),
              (cliente_id, cliente_nombre, session['user'],
               request.form['descripcion'], float(request.form['monto']),
               request.form.get('estatus','Pendiente')))
    conn.commit(); conn.close(); return redirect('/facturacion')

@app.route('/facturacion/estatus/<int:fid>', methods=['POST'])
def cambiar_estatus_factura(fid):
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q('UPDATE facturas SET estatus=? WHERE id=?'), (request.form['estatus'], fid))
    conn.commit(); conn.close(); return redirect('/facturacion')

@app.route('/facturacion/eliminar/<int:fid>', methods=['POST'])
def eliminar_factura(fid):
    if 'user' not in session or session['role'] != 'admin': return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q('DELETE FROM facturas WHERE id=?'), (fid,)); conn.commit(); conn.close()
    return redirect('/facturacion')

@app.route('/perfil', methods=['GET','POST'])
def perfil():
    if 'user' not in session: return redirect('/')
    conn = db(); c = conn.cursor()
    c.execute(q('SELECT * FROM users WHERE username=?'), (session['user'],)); user = fetchone(c)
    if request.method == 'POST':
        new_pass = request.form.get('password','').strip()
        if new_pass:
            c.execute(q('UPDATE users SET nombre=?,email=?,telefono=?,password=? WHERE username=?'),
                      (request.form['nombre'], request.form.get('email',''),
                       request.form.get('telefono',''), new_pass, session['user']))
        else:
            c.execute(q('UPDATE users SET nombre=?,email=?,telefono=? WHERE username=?'),
                      (request.form['nombre'], request.form.get('email',''),
                       request.form.get('telefono',''), session['user']))
        conn.commit(); session['nombre'] = request.form['nombre']; conn.close()
        return redirect('/dashboard')
    conn.close()
    return render_template('perfil.html', user=user, nombre=session['nombre'], role=session['role'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
