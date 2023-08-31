from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
import uuid

app = Flask(__name__)
socketio = SocketIO(app)

def generate_unique_id():
    return str(uuid.uuid4())

# Définition des classes Calibre et Commande
class Calibre:
    def __init__(self, nom, description):
        self.nom = nom
        self.description = description

class Commande:
    def __init__(self, id, nom, calibre, nombre_palettes, nombre_palettes_realisees=0):
        self.id = id
        self.nom = nom
        self.calibre = calibre
        self.nombre_palettes = nombre_palettes
        self.nombre_palettes_realisees = nombre_palettes_realisees

    def to_dict(self):
        return {
            'nom': self.nom,
            'calibre': self.calibre.__dict__,
            'nombre_palettes': self.nombre_palettes,
            'nombre_palettes_realisees': self.nombre_palettes_realisees
        }
    
    @property
    def status_class(self):
        if self.nombre_palettes-self.nombre_palettes_realisees <= 1:
            return 'rouge'
        elif self.nombre_palettes-self.nombre_palettes_realisees <= 3:
            return 'orange'
        else:
            return 'vert'

calibres = {
    "11": Calibre("11", "Calibre 11"),
    "12Q": Calibre("12Q", "Calibre 12Q"),
    "12L": Calibre("12L", "Calibre 12L"),
    "9": Calibre("9", "Calibre 9"),
    "15": Calibre("15", "Calibre 15"),
    "18": Calibre("18", "Calibre 18"),
}

commandes_par_calibre = {
    "11": [],
    "12Q": [],
    "12L": [],
    "9": [],
    "15": [],
    "18": [],
}

@app.route('/')
def accueil():
    return render_template('accueil.html')

@app.route('/maj-commandes', methods=['GET', 'POST'])
def maj_commandes():
    if request.method == 'POST':
        nom = request.form['nom']
        calibre = calibres[request.form['calibre']]
        nombre_palettes = int(request.form['nombre_palettes'])
        
        nouvelle_commande = Commande(nom, calibre, nombre_palettes)
        commandes_par_calibre[calibre.nom].append(nouvelle_commande)

        # Émettre la mise à jour des commandes à tous les clients via SocketIO
        commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
        socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})

        return redirect(url_for('maj_commandes'))

    return render_template('maj_commandes.html', calibres=calibres, commandes_par_calibre=commandes_par_calibre)

@app.route('/ajouter-commande', methods=['GET', 'POST'])
def ajouter_commande():
    if request.method == 'POST':
        nom = request.form['nom']
        calibre = calibres[request.form['calibre']]
        nombre_palettes = int(request.form['nombre_palettes'])
        id = generate_unique_id()
        
        nouvelle_commande = Commande(id, nom, calibre, nombre_palettes)
        commandes_par_calibre[calibre.nom].append(nouvelle_commande)

        # Émettre la mise à jour des commandes à tous les clients via SocketIO
        commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
        socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})

        return redirect(url_for('maj_commandes'))

    return render_template('ajouter_commande.html', calibres=calibres)

@app.route('/liste-commandes')
def liste_commandes():
    return render_template('liste_commandes.html', commandes_par_calibre=commandes_par_calibre)

@app.route('/incrementer-palettes/<string:commande_id>')
def incrementer_palettes(commande_id):
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                cmd.nombre_palettes_realisees += 1
                break

    # Émettre la mise à jour des commandes à tous les clients via SocketIO
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})

    return redirect(url_for('maj_commandes'))

@app.route('/decrementer-palettes/<string:commande_id>')
def decrementer_palettes(commande_id):
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id and cmd.nombre_palettes_realisees > 0:
                cmd.nombre_palettes_realisees -= 1
                break

    # Émettre la mise à jour des commandes à tous les clients via SocketIO
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})

    return redirect(url_for('maj_commandes'))

@app.route('/modifier-commande/<string:commande_id>', methods=['GET', 'POST'])
def modifier_commande(commande_id):
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                if request.method == 'POST':
                    cmd.nom = request.form['nom']
                    cmd.calibre = calibres[request.form['calibre']]
                    cmd.nombre_palettes = int(request.form['nombre_palettes'])

                    # Émettre la mise à jour des commandes à tous les clients via SocketIO
                    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
                    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})

                    return redirect(url_for('maj_commandes'))

                return render_template('modifier_commande.html', calibres=calibres, commande=cmd)

    return redirect(url_for('maj_commandes'))

@app.route('/supprimer-commande/<string:commande_id>')
def supprimer_commande(commande_id):
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                commandes.remove(cmd)
                # Émettre la mise à jour des commandes à tous les clients via SocketIO
                commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
                socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
                break

    return redirect(url_for('maj_commandes'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
