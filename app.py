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


def dictfetchone(cursor):
    row = cursor.fetchone()
    if not row:
        return None
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def dictfetchall(cursor):
    rows = cursor.fetchall()
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in rows]

# ================= INIT DB =================

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        nombre TEXT,
        email TEXT,
        telefono TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        apellido TEXT,
        telefono TEXT,
        email TEXT,
        tipo TEXT,
        estatus TEXT DEFAULT 'Nuevo',
        asesor TEXT,
        asesor_nombre TEXT,
        notas TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS jornadas (
        id SERIAL PRIMARY KEY,
        nombre TEXT,
        asesor TEXT,
        fase TEXT,
        activa INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS facturas (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER,
        cliente_nombre TEXT,
        asesor TEXT,
        descripcion TEXT,
        monto REAL,
        estatus TEXT DEFAULT 'Pendiente',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # USERS
    c.execute("SELECT 1 FROM users WHERE username='admin'")
    if not c.fetchone():
        users = [
            ('admin','1234','admin','Victor Perez','admin@vp.com','0414-000'),
            ('asesor1','1234','asesor','Kayret Licet','k@vp.com','0414-111'),
            ('asesor2','1234','asesor','Andreina Molina','a@vp.com','0424-222'),
            ('asesor3','1234','asesor','Luis Fermin','l@vp.com','0412-333'),
        ]
        for u in users:
            c.execute("INSERT INTO users(username,password,role,nombre,email,telefono) VALUES(%s,%s,%s,%s,%s,%s)", u)

    # CLIENTS
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        today = date.today()
        clients = [
            ('Maria','Gonzalez','0414','m@gmail.com','Nuevo','Nuevo','asesor1','Kayret Licet','Interesada',today),
            ('Pedro','Hernandez','0424','p@gmail.com','Referido','Seguimiento','asesor1','Kayret Licet','Referido',today),
        ]
        for cl in clients:
            c.execute("""
            INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, cl)

    conn.commit()
    conn.close()

init_db()

# ================= LOGIN =================

@app.route('/', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        conn = db()
        c = conn.cursor()
        c.execute("SELECT username,role,nombre FROM users WHERE username=%s AND password=%s",
                  (request.form['username'], request.form['password']))
        user = dictfetchone(c)
        conn.close()

        if user:
            session['user'] = user['username']
            session['role'] = user['role']
            session['nombre'] = user['nombre']
            return redirect('/dashboard')

        error = "Credenciales incorrectas"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= DASHBOARD =================

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    conn = db()
    c = conn.cursor()
    today = date.today()

    if session['role'] == 'admin':
        c.execute("SELECT * FROM users WHERE role='asesor'")
        asesores = dictfetchall(c)

        data = []
        for a in asesores:
            c.execute("SELECT COUNT(*) FROM clients WHERE asesor=%s", (a['username'],))
            cnt = c.fetchone()[0]
            data.append({'asesor': a, 'clientes_hoy': cnt})

        c.execute("SELECT * FROM jornadas WHERE activa=1")
        jornadas = dictfetchall(c)

        conn.close()
        return render_template('dashboard_admin.html',
                               asesores_data=data,
                               jornadas=jornadas,
                               nombre=session['nombre'],
                               role=session['role'])

    else:
        c.execute("SELECT * FROM clients WHERE asesor=%s ORDER BY id DESC", (session['user'],))
        clients = dictfetchall(c)

        c.execute("SELECT COUNT(*) FROM clients WHERE asesor=%s", (session['user'],))
        hoy = c.fetchone()[0]

        conn.close()
        return render_template('dashboard_asesor.html',
                               clients=clients,
                               total=len(clients),
                               hoy=hoy,
                               nombre=session['nombre'],
                               role=session['role'])

# ================= CLIENTES =================

@app.route('/clientes')
def clientes():
    if 'user' not in session:
        return redirect('/')

    conn = db()
    c = conn.cursor()

    if session['role'] == 'admin':
        c.execute("SELECT * FROM clients ORDER BY id DESC")
    else:
        c.execute("SELECT * FROM clients WHERE asesor=%s ORDER BY id DESC", (session['user'],))

    clients = dictfetchall(c)
    conn.close()

    return render_template('clientes.html', clients=clients)

@app.route('/clientes/nuevo', methods=['GET','POST'])
def nuevo_cliente():
    if request.method == 'POST':
        conn = db()
        c = conn.cursor()

        c.execute("SELECT nombre FROM users WHERE username=%s", (session['user'],))
        asesor_nombre = c.fetchone()[0]

        c.execute("""
        INSERT INTO clients(nombre,apellido,telefono,email,tipo,estatus,asesor,asesor_nombre,notas)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['nombre'],
            request.form['apellido'],
            request.form['telefono'],
            request.form['email'],
            request.form['tipo'],
            'Nuevo',
            session['user'],
            asesor_nombre,
            request.form['notas']
        ))

        conn.commit()
        conn.close()
        return redirect('/clientes')

    return render_template('cliente_form.html')

@app.route('/clientes/editar/<int:id>', methods=['GET','POST'])
def editar_cliente(id):
    conn = db()
    c = conn.cursor()

    if request.method == 'POST':
        c.execute("""
        UPDATE clients SET nombre=%s,apellido=%s,telefono=%s,email=%s,tipo=%s,estatus=%s,notas=%s
        WHERE id=%s
        """, (
            request.form['nombre'],
            request.form['apellido'],
            request.form['telefono'],
            request.form['email'],
            request.form['tipo'],
            request.form['estatus'],
            request.form['notas'],
            id
        ))
        conn.commit()
        conn.close()
        return redirect('/clientes')

    c.execute("SELECT * FROM clients WHERE id=%s", (id,))
    client = dictfetchone(c)
    conn.close()

    return render_template('cliente_form.html', client=client)

@app.route('/clientes/eliminar/<int:id>', methods=['POST'])
def eliminar_cliente(id):
    if session.get('role') != 'admin':
        return redirect('/')

    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM clients WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect('/clientes')

# ================= USUARIOS =================

@app.route('/usuarios')
def usuarios():
    if session.get('role') != 'admin':
        return redirect('/')

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY role")
    users = dictfetchall(c)
    conn.close()

    return render_template('usuarios.html', users=users)

# ================= FACTURACION =================

@app.route('/facturacion')
def facturacion():
    if session.get('role') != 'admin':
        return redirect('/')

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM facturas ORDER BY id DESC")
    facturas = dictfetchall(c)
    conn.close()

    return render_template('facturacion.html', facturas=facturas)

# ================= PERFIL =================

@app.route('/perfil')
def perfil():
    if 'user' not in session:
        return redirect('/')

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=%s", (session['user'],))
    user = dictfetchone(c)
    conn.close()

    return render_template('perfil.html', user=user)

# ================= RUN =================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
