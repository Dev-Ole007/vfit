from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'vfitnes_secret_key_1234'  # Para mensagens flash

DB_NAME = 'database.db'

# --- Banco de dados ---
def conectar():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_banco():
    if not os.path.exists(DB_NAME):
        conn = conectar()
        cur = conn.cursor()
        # Usuários com status de pagamento (Pago ou Não Pago)
        cur.execute('''
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                pago INTEGER DEFAULT 0 -- 0 = não pago, 1 = pago
            )
        ''')
        # Acessos registrados (quem, data, hora)
        cur.execute('''
            CREATE TABLE acessos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                horario TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

inicializar_banco()

# --- Rotas ---

@app.route('/')
def index():
    return redirect(url_for('login'))

# Cadastro
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome').strip()
        usuario = request.form.get('usuario').strip()
        senha = request.form.get('senha').strip()
        pago = 1 if request.form.get('pago') == 'on' else 0

        if not nome or not usuario or not senha:
            flash('Por favor, preencha todos os campos.')
            return redirect(url_for('cadastro'))

        conn = conectar()
        try:
            conn.execute('INSERT INTO usuarios (nome, usuario, senha, pago) VALUES (?, ?, ?, ?)',
                         (nome, usuario, senha, pago))
            conn.commit()
            flash('Cadastro realizado com sucesso. Faça login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe. Escolha outro.')
            return redirect(url_for('cadastro'))
        finally:
            conn.close()

    return render_template('cadastro.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario').strip()
        senha = request.form.get('senha').strip()

        conn = conectar()
        user = conn.execute('SELECT * FROM usuarios WHERE usuario = ? AND senha = ?', (usuario, senha)).fetchone()
        conn.close()

        if user:
            registrar_acesso(usuario)
            return redirect(url_for('painel', usuario=usuario))
        else:
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('login'))
    return render_template('login.html')

# Registrar acesso
def registrar_acesso(usuario):
    agora = datetime.now()
    conn = conectar()
    conn.execute('INSERT INTO acessos (usuario, horario, data) VALUES (?, ?, ?)',
                 (usuario, agora.strftime('%H:%M:%S'), agora.strftime('%d/%m/%Y')))
    conn.commit()
    conn.close()

# Painel principal
@app.route('/painel/<usuario>')
def painel(usuario):
    conn = conectar()
    user = conn.execute('SELECT * FROM usuarios WHERE usuario = ?', (usuario,)).fetchone()
    conn.close()
    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('login'))
    return render_template('painel.html', usuario=user['usuario'], nome=user['nome'], pago=user['pago'])

# Histórico - dividido geral e hoje
@app.route('/historico')
def historico():
    conn = conectar()
    hoje = datetime.now().strftime('%d/%m/%Y')
    historico_geral = conn.execute('SELECT * FROM acessos ORDER BY usuario COLLATE NOCASE ASC, data DESC, horario DESC').fetchall()
    historico_hoje = conn.execute('SELECT * FROM acessos WHERE data = ? ORDER BY usuario COLLATE NOCASE ASC, horario DESC', (hoje,)).fetchall()
    conn.close()
    return render_template('historico.html', historico_geral=historico_geral, historico_hoje=historico_hoje, hoje=hoje)

# Lista usuários com status pagamento
@app.route('/usuarios')
def usuarios():
    conn = conectar()
    users = conn.execute('SELECT * FROM usuarios ORDER BY nome COLLATE NOCASE ASC').fetchall()
    conn.close()
    return render_template('usuarios.html', users=users)

# Alterar status pagamento - simples toggle
@app.route('/alterar_pagamento/<usuario>')
def alterar_pagamento(usuario):
    conn = conectar()
    user = conn.execute('SELECT * FROM usuarios WHERE usuario = ?', (usuario,)).fetchone()
    if user:
        novo_status = 0 if user['pago'] == 1 else 1
        conn.execute('UPDATE usuarios SET pago = ? WHERE usuario = ?', (novo_status, usuario))
        conn.commit()
        flash(f'Status de pagamento de {usuario} alterado.')
    conn.close()
    return redirect(url_for('usuarios'))


@app.route('/enviar_aviso')
def enviar_aviso():
    
    conn = conectar()
    inadimplentes = conn.execute('SELECT nome, usuario FROM usuarios WHERE pago = 0').fetchall()
    conn.close()

    if not inadimplentes:
        flash('Todos estão pagos! Nenhum aviso enviado.')
    else:
        print('=== AVISOS para inadimplentes ===')
        for user in inadimplentes:
            print(f'Enviando mensagem para {user["nome"]} ({user["usuario"]}) no WhatsApp...')
        flash(f'Aviso simulado enviado para {len(inadimplentes)} inadimplentes (veja no console).')

    return redirect(url_for('usuarios'))

if __name__ == '__main__':
    app.run(debug=True)
