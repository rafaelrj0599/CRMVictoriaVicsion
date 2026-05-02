from flask import Flask, render_template, request, redirect, session
from datetime import date
import random
import os
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'victoria_vicsion_secret_v3')

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise Exception("DATABASE_URL no configurada")

# ================= DB =================

def db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')


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

# ================= INIT DB =================

def init_db():
    conn = db()
    c = conn.cursor()

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

    # Usuarios por defecto
    c.execute("SELECT 1 FROM users WHERE username='admin'")
    if not fetchone(c):
        usuarios = [
            ('admin','1234','admin','Victor Perez','admin@victoriavicsion.com','0414-0000001'),
            ('asesor1','1234','asesor','Kayret Licet','kayret@victoriavicsion.com','0414-1234567'),
            ('asesor2','1234','asesor','Andreina Molina','andreina@victoriavicsion.com','0424-2345678'),
            ('asesor3','1234','asesor','Luis Fermin','luis@victoriavicsion.com','0412-3456789'),
            ('asesor4','1234','asesor','Daniela Rios','daniela@victoriavicsion.com','0426-4567890'),
        ]
        for u in usuarios:
            c.execute("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(%s,%s,%s,%s,%s,%s)", u)

    # Clients
    c.execute("SELECT COUNT(*) AS total FROM clients")
    row = fetchone(c)
    if row["total"] == 0:
        today = date.today()
        clients = [
            ('Maria','Gonzalez','0414-1111111','maria@gmail.com','Nuevo','Nuevo','asesor1','Kayret Licet','Interesada en jornada',today),
            ('Pedro','Hernandez','0424-2222222','pedro@gmail.com','Referido','En seguimiento','asesor1','Kayret Licet','Referido por Gonzalez',today),
        ]
        for cl in clients:
            c.execute('''INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas,created_at)
                         VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''', cl)

    # Jornadas
    c.execute("SELECT COUNT(*) AS total FROM jornadas")
    row = fetchone(c)
    if row["total"] == 0:
        fases = ['Captacion','Prospeccion','Seguimiento','Cierre','Postventa']
        jornadas = [
            ('Jornada Matutina Abril','asesor1',random.choice(fases),1),
            ('Jornada Tarde Mayo','asesor2',random.choice(fases),1),
        ]
        for j in jornadas:
            c.execute("INSERT INTO jornadas(nombre,asesor,fase,activa) VALUES(%s,%s,%s,%s)", j)

    conn.commit()
    conn.close()

init_db()

# ================= ROUTES =================

@app.route('/', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        conn = db(); c = conn.cursor()
        c.execute('SELECT username,role,nombre FROM users WHERE username=%s AND password=%s',
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
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect('/')
    conn = db(); c = conn.cursor()
    today = date.today()

    if session['role'] == 'admin':
        c.execute("SELECT * FROM users WHERE role='asesor'")
        asesores = fetchall(c)

        asesores_data = []
        for a in asesores:
            c.execute("SELECT COUNT(*) AS cnt FROM clients WHERE asesor=%s AND created_at::date=%s",
                      (a['username'], today))
            row = fetchone(c)
            asesores_data.append({'asesor': a, 'clientes_hoy': row['cnt']})

        c.execute("SELECT j.*, u.nombre as asesor_nombre FROM jornadas j LEFT JOIN users u ON j.asesor=u.username WHERE j.activa=1")
        jornadas = fetchall(c)
        conn.close()

        return render_template('dashboard_admin.html',
                               asesores_data=asesores_data,
                               jornadas=jornadas,
                               nombre=session['nombre'],
                               role=session['role'])
    else:
        c.execute("SELECT * FROM clients WHERE asesor=%s ORDER BY id DESC", (session['user'],))
        clients = fetchall(c)

        c.execute("SELECT COUNT(*) AS cnt FROM clients WHERE asesor=%s AND created_at::date=%s",
                  (session['user'], today))
        row = fetchone(c)

        conn.close()

        return render_template('dashboard_asesor.html',
                               clients=clients,
                               total=len(clients),
                               hoy=row['cnt'],
                               nombre=session['nombre'],
                               role=session['role'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
