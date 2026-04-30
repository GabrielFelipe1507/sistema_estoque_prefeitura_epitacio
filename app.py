from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "estoque_epitacio_2026"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque_prefeitura_epitacio.db'
db = SQLAlchemy(app)

# Modelos
class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)

# Mantenha o modelo Item com as novas colunas como fizemos antes:
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    categoria_nome = db.Column(db.String(50))
    descricao = db.Column(db.String(100))
    patrimonio = db.Column(db.String(50), nullable=True)
    quantidade = db.Column(db.Integer, default=0)
    marca = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(30), default='Indefinido')
    baixa = db.Column(db.String(20), default='Indefinido')
    descarte = db.Column(db.String(20), default='Indefinido')
    descricao_baixa = db.Column(db.String(200), nullable=True)

class Cor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True)

with app.app_context():
    db.create_all()
    if not Categoria.query.first():
        lista = ["Tubinhos de Tinta/ Refil", "Cartuchos", "Toner", "Monitores", "CPU's", "Teclados", "Mouses", "Nobrakes", "Estabilizadores", "Notebooks", "Fontes", "Caixinhas de Som", "Coolers", "Baterias de Carro"]
        for c in lista: db.session.add(Categoria(nome=c))
        db.session.commit()
    if not Cor.query.first():
        for c in ['Amarelo', 'Preto', 'Magenta', 'Cyan (Azul)']: db.session.add(Cor(nome=c))
        db.session.commit()

@app.route('/')
def index():
    categorias = Categoria.query.all()
    cat_selecionada = request.args.get('cat', categorias[0].nome if categorias else "")
    search_query = request.args.get('search', '')
    sort_order = request.args.get('sort', 'asc')
    query = Item.query.filter_by(categoria_nome=cat_selecionada)
    if search_query:
        query = query.filter(Item.descricao.contains(search_query) | Item.patrimonio.contains(search_query) | Item.marca.contains(search_query))
    if sort_order == 'asc':
        query = query.order_by(Item.descricao.asc())
    else:
        query = query.order_by(Item.descricao.desc())
    itens = query.all()
    cores = Cor.query.all()
    return render_template('index.html', itens=itens, cores=cores, categorias=categorias, cat_ativa=cat_selecionada, search=search_query, sort=sort_order)

@app.route('/add', methods=['POST'])
def add():
    cat = request.form.get('categoria')
    novo = Item(
        categoria_nome=cat, 
        descricao=request.form.get('descricao'), 
        patrimonio=request.form.get('patrimonio'),
        quantidade=int(request.form.get('quantidade', 0)), 
        marca=request.form.get('marca'), 
        status=request.form.get('status', 'Indefinido'),
        baixa=request.form.get('baixa', 'Indefinido'),
        descarte=request.form.get('descarte', 'Indefinido'),
        descricao_baixa=request.form.get('descricao_baixa')
    )
    db.session.add(novo); db.session.commit()
    return redirect(url_for('index', cat=cat))

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    item = Item.query.get_or_404(id)
    if request.method == 'POST':
        item.descricao = request.form.get('descricao')
        item.patrimonio = request.form.get('patrimonio')
        item.quantidade = int(request.form.get('quantidade', 0))
        item.marca = request.form.get('marca')
        item.status = request.form.get('status', 'Indefinido')
        item.baixa = request.form.get('baixa', 'Indefinido')
        item.descarte = request.form.get('descarte', 'Indefinido')
        item.descricao_baixa = request.form.get('descricao_baixa')
        db.session.commit()
        return redirect(url_for('index', cat=item.categoria_nome))
    return render_template('editar.html', item=item)

# Outras rotas (delete, add_color, etc) permanecem iguais...
@app.route('/delete/<int:id>')
def delete(id):
    item = Item.query.get(id); cat = item.categoria_nome
    db.session.delete(item); db.session.commit()
    return redirect(url_for('index', cat=cat))

@app.route('/add_category', methods=['POST'])
def add_category():
    nome = request.form.get('nova_categoria')
    if nome and not Categoria.query.filter_by(nome=nome).first():
        db.session.add(Categoria(nome=nome)); db.session.commit()
    return redirect(url_for('index', cat=nome))

@app.route('/delete_category/<string:nome>')
def delete_category(nome):
    if Item.query.filter_by(categoria_nome=nome).count() > 0:
        flash(f"Não é possível excluir '{nome}': existem itens cadastrados!")
    else:
        cat = Categoria.query.filter_by(nome=nome).first()
        if cat: db.session.delete(cat); db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_color', methods=['POST'])
def add_color():
    nova_cor = request.form.get('nova_cor')
    if nova_cor:
        try: db.session.add(Cor(nome=nova_cor)); db.session.commit()
        except: db.session.rollback()
    return redirect(url_for('index'))

@app.route('/delete_color/<int:id>')
def delete_color(id):
    cor = Cor.query.get(id)
    if cor: db.session.delete(cor); db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)