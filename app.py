import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.secret_key = "seguranca_epitacio_2026" # Sua chave de segurança

# --- CONFIGURAÇÃO DE E-MAIL ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'epitacioinformatica2021@gmail.com'

# AQUI ESTÁ A SUA SENHA QUE VOCÊ GEROU (SEM ESPAÇOS)
app.config['MAIL_PASSWORD'] = 'ysteqfayvzilatnd' 

# Esta linha abaixo "liga" o sistema de e-mail com as configurações acima
mail = Mail(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque_prefeitura_epitacio.db'
db = SQLAlchemy(app)

@app.after_request
def add_header(response):
    """
    Adiciona cabeçalhos para impedir que o navegador armazene a página no cache.
    Isso impede que o botão 'Voltar' mostre dados após o Logout.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# CONFIGURAÇÃO DO LOGIN (Vem aqui porque precisa do 'app' criado acima)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS ---
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False) # Novo campo
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False) # Aumentei o tamanho para o hash

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    colunas = db.Column(db.String(500), default="") 

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    categoria_nome = db.Column(db.String(50))
    # Campos base do banco (usados apenas quando a categoria permitir)
    descricao = db.Column(db.String(100), default="")
    quantidade = db.Column(db.Integer, default=0)
    marca = db.Column(db.String(50), default="")
    dados_dinamicos = db.Column(db.Text, default="{}") 

class Cor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)

# --- INICIALIZAÇÃO ---
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(email='admin@gmail.com').first():
        # Agora a senha '123456' vira um código gigante e seguro
        senha_hash = generate_password_hash('123456')
        admin = Usuario(nome="Administrador", email='admin@gmail.com', senha=senha_hash)
        db.session.add(admin)
        db.session.commit()

    if not Categoria.query.first():
        # Configuração inicial para garantir que os consumíveis tenham seus campos extras
        db.session.add(Categoria(nome="Tubinhos de Tinta/ Refil", colunas="Status"))
        db.session.add(Categoria(nome="Cartuchos", colunas=""))
        db.session.add(Categoria(nome="Toner", colunas="Status"))
        
        p_completo = "Patrimônio, Status, Baixa, Descarte, Destino"
        padroes = ["Monitores", "CPU's", "Teclados", "Mouses", "Notebooks"]
        for p in padroes:
            db.session.add(Categoria(nome=p, colunas=p_completo))
        db.session.commit()

# --- ROTAS PRINCIPAIS ---

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        user = Usuario.query.filter_by(email=email).first()
        
        # No def login():
        if user and check_password_hash(user.senha, senha): # Verificação segura
            login_user(user)
            return redirect(url_for('index'))
        flash('E-mail ou senha incorretos!', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Usuario.query.filter_by(email=email).first()
        
        if user:
            import secrets, string
            # Gera uma senha aleatória de 8 caracteres
            nova_senha = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            
            # --- O AJUSTE ESTÁ AQUI ---
            # Transformamos a senha em HASH antes de salvar no banco
            user.senha = generate_password_hash(nova_senha) 
            db.session.commit()
            
            # Enviamos a senha "limpa" por e-mail para o usuário conseguir ler
            msg = Message("Sua Nova Senha - Estoque Prefeitura",
                          sender="epitacioinformatica2021@gmail.com",
                          recipients=[email])
            msg.body = f"Olá! Sua nova senha temporária para o sistema de Epitácio é: {nova_senha}"
            mail.send(msg)
            
            flash('Uma nova senha foi enviada para o seu e-mail!', 'success')
            return redirect(url_for('login'))
        flash('E-mail não encontrado!', 'danger')
    return render_template('recuperar_senha.html')

@app.route('/')
@login_required
def index():
    categorias = Categoria.query.all()
    if not categorias:
        return redirect(url_for('gerenciar_categorias'))
        
    cat_selecionada = request.args.get('cat', categorias[0].nome if categorias else "")
    search = request.args.get('search', '')
    sort_order = request.args.get('sort', 'asc')
    
    query = Item.query.filter_by(categoria_nome=cat_selecionada)
    if search:
        query = query.filter(Item.descricao.contains(search) | Item.marca.contains(search) | Item.dados_dinamicos.contains(search))
    
    if sort_order == 'asc':
        query = query.order_by(Item.descricao.asc())
    else:
        query = query.order_by(Item.descricao.desc())
        
    itens = query.all()
    for item in itens:
        item.dicionario = json.loads(item.dados_dinamicos) if item.dados_dinamicos else {}

    cat_info = Categoria.query.filter_by(nome=cat_selecionada).first()
    lista_colunas = [c.strip() for c in cat_info.colunas.split(',')] if cat_info and cat_info.colunas else []

    return render_template('index.html', itens=itens, categorias=categorias, cat_ativa=cat_selecionada, 
                           search=search, sort=sort_order, cat_info=cat_info, lista_colunas=lista_colunas, cores=Cor.query.all())

@app.route('/add', methods=['POST'])
@login_required # <--- Adicione aqui
def add():
    cat = request.form.get('categoria')
    
    # Captura campos dinâmicos (prefixados com dyn_)
    dados_dinamicos = {}
    for key, value in request.form.items():
        if key.startswith('dyn_'):
            dados_dinamicos[key.replace('dyn_', '')] = value

    # Captura campos fixos apenas se estiverem presentes no form (proteção para não duplicar marca)
    novo = Item(
        categoria_nome=cat,
        descricao=request.form.get('descricao', ''),
        quantidade=int(request.form.get('quantidade', 0)) if request.form.get('quantidade') else 0,
        marca=request.form.get('marca', ''),
        dados_dinamicos=json.dumps(dados_dinamicos)
    )
    db.session.add(novo)
    db.session.commit()
    return redirect(url_for('index', cat=cat))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required # <--- Adicione aqui
def editar(id):
    item = db.session.get(Item, id) # Novo padrão SQLAlchemy 2.0
    if not item:
        return redirect(url_for('index'))
        
    cat_info = Categoria.query.filter_by(nome=item.categoria_nome).first()
    lista_colunas = [c.strip() for c in cat_info.colunas.split(',')] if cat_info and cat_info.colunas else []
    
    if request.method == 'POST':
        # Atualiza fixos se for consumível
        if item.categoria_nome in ["Cartuchos", "Toner", "Tubinhos de Tinta/ Refil"]:
            item.descricao = request.form.get('descricao')
            item.quantidade = int(request.form.get('quantidade', 0))
            item.marca = request.form.get('marca')
        
        # Atualiza dinâmicos
        dados_novos = {}
        for key, value in request.form.items():
            if key.startswith('dyn_'):
                dados_novos[key.replace('dyn_', '')] = value
        
        item.dados_dinamicos = json.dumps(dados_novos)
        db.session.commit()
        return redirect(url_for('index', cat=item.categoria_nome))
    
    item.dicionario = json.loads(item.dados_dinamicos) if item.dados_dinamicos else {}
    return render_template('editar.html', item=item, lista_colunas=lista_colunas)

@app.route('/delete/<int:id>')
@login_required # <--- Adicione aqui
def delete(id):
    item = db.session.get(Item, id)
    if item:
        cat = item.categoria_nome
        db.session.delete(item)
        db.session.commit()
        return redirect(url_for('index', cat=cat))
    return redirect(url_for('index'))

# --- GERENCIAMENTO DE CATEGORIAS ---

@app.route('/gerenciar_categorias')
@login_required
def gerenciar_categorias():
    return render_template('gerenciar_categorias.html', categorias=Categoria.query.all())

@app.route('/salvar_categoria', methods=['POST'])
@login_required # <--- Adicione aqui
def salvar_categoria():
    cat_id = request.form.get('cat_id')
    nome = request.form.get('nome').strip()
    colunas_lista = request.form.getlist('coluna[]')
    colunas_str = ",".join([c.strip() for c in colunas_lista if c.strip()])

    if cat_id and cat_id.isdigit():
        cat = db.session.get(Categoria, int(cat_id))
        if cat:
            if cat.nome != nome:
                Item.query.filter_by(categoria_nome=cat.nome).update({"categoria_nome": nome})
            cat.nome = nome
            cat.colunas = colunas_str
            flash("Categoria atualizada!")
    else:
        if not Categoria.query.filter_by(nome=nome).first():
            db.session.add(Categoria(nome=nome, colunas=colunas_str))
            flash("Categoria criada!")
        else:
            flash("Esta categoria já existe!", "error")
            
    db.session.commit()
    return redirect(url_for('gerenciar_categorias'))

@app.route('/excluir_categoria/<int:id>')
@login_required # <--- Adicione aqui
def excluir_categoria(id):
    cat = db.session.get(Categoria, id)
    if cat:
        if Item.query.filter_by(categoria_nome=cat.nome).count() > 0:
            flash("Não é possível excluir: categoria possui itens!")
        else:
            db.session.delete(cat)
            db.session.commit()
            flash("Categoria excluída!")
    return redirect(url_for('gerenciar_categorias'))

# --- CORES ---

@app.route('/add_color', methods=['POST'])
@login_required # <--- Adicione aqui
def add_color():
    nova_cor = request.form.get('nova_cor')
    if nova_cor and not Cor.query.filter_by(nome=nova_cor).first():
        db.session.add(Cor(nome=nova_cor))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_color/<int:id>')
@login_required # <--- Adicione aqui
def delete_color(id):
    cor = db.session.get(Cor, id)
    if cor:
        db.session.delete(cor)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/gerenciar_usuarios')
@login_required
def gerenciar_usuarios():
    search = request.args.get('search', '')
    if search:
        usuarios = Usuario.query.filter(Usuario.nome.contains(search) | Usuario.email.contains(search)).all()
    else:
        usuarios = Usuario.query.all()
    return render_template('gerenciar_usuarios.html', usuarios=usuarios, search=search)

@app.route('/salvar_usuario', methods=['POST'])
@login_required
def salvar_usuario():
    user_id = request.form.get('user_id')
    nome = request.form.get('nome')
    email = request.form.get('email')
    senha = request.form.get('senha')

    if user_id: # EDITAR
        user = db.session.get(Usuario, int(user_id))
        user.nome = nome
        user.email = email
        if senha: # Só muda a senha se o usuário digitou uma nova
            user.senha = generate_password_hash(senha)
        flash("Usuário atualizado com sucesso!")
    else: # CRIAR NOVO
        if Usuario.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado!", "danger")
        else:
            novo_user = Usuario(nome=nome, email=email, senha=generate_password_hash(senha))
            db.session.add(novo_user)
            flash("Usuário criado com sucesso!")
    
    db.session.commit()
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/excluir_usuario/<int:id>')
@login_required
def excluir_usuario(id):
    if id == current_user.id:
        flash("Você não pode excluir a si mesmo!", "danger")
    else:
        user = db.session.get(Usuario, id)
        db.session.delete(user)
        db.session.commit()
        flash("Usuário removido!")
    return redirect(url_for('gerenciar_usuarios'))

if __name__ == '__main__':
    # host='0.0.0.0' permite que o servidor seja encontrado na rede local
    app.run(debug=True, host='0.0.0.0', port=5000)