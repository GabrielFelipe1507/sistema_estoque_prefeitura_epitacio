import json
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "estoque_epitacio_2026"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque_prefeitura_epitacio.db'
db = SQLAlchemy(app)

# --- MODELOS ---

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

@app.route('/')
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
def gerenciar_categorias():
    return render_template('gerenciar_categorias.html', categorias=Categoria.query.all())

@app.route('/salvar_categoria', methods=['POST'])
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
def add_color():
    nova_cor = request.form.get('nova_cor')
    if nova_cor and not Cor.query.filter_by(nome=nova_cor).first():
        db.session.add(Cor(nome=nova_cor))
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_color/<int:id>')
def delete_color(id):
    cor = db.session.get(Cor, id)
    if cor:
        db.session.delete(cor)
        db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)