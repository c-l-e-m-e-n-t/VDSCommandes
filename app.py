from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO
import uuid
import json

app = Flask(__name__)
socketio = SocketIO(app)

checkbox_states = {}
volume = 0

def generate_unique_id():
    return str(uuid.uuid4())

def sauvegarder_commandes():
    #enregistrer dans un json
    commandes_json = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    with open('saves/commandes.json', 'w') as file:
        json.dump(commandes_json, file)

def get_completed_state(self):
    cookie_name = f'completed_{self.id}'
    return request.cookies.get(cookie_name, 'false') == 'true'

def charger_commandes(filename):
    try:
        with open('saves/'+filename, 'r') as file:
            commandes_json = json.load(file)
            commandes_par_calibre = {}
            for calibre, commandes in commandes_json.items():
                commandes_par_calibre[calibre] = []
                for cmd in commandes:
                    commandes_par_calibre[calibre].append(Commande(cmd['id'], cmd['nom'], calibres[cmd['calibre']['nom']], cmd['nombre_palettes'], cmd['nombre_colis'], cmd['nombre_palettes_realisees']))
            return commandes_par_calibre
    except FileNotFoundError:
        # Si le fichier n'existe pas (première exécution), retournez un dictionnaire vide
        return {}

# Définition des classes Calibre et Commande
class Calibre:
    def __init__(self, nom, description):
        self.nom = nom
        self.description = description

class Commande:
    def __init__(self, id, nom, calibre, nombre_palettes, nombre_colis, nombre_palettes_realisees=0):
        self.id = id
        self.nom = nom
        self.calibre = calibre
        self.nombre_palettes = nombre_palettes
        self.nombre_colis = ""
        if type(nombre_colis) == int:
            if nombre_colis > 0 :
                self.nombre_colis = "|| Colis : " + str(nombre_colis)
        self.nombre_palettes_realisees = nombre_palettes_realisees

    def to_dict(self):
        return {
            'id': self.id,
            'nom': self.nom,
            'calibre': self.calibre.__dict__,
            'nombre_palettes': self.nombre_palettes,
            'nombre_colis': self.nombre_colis,
            'nombre_palettes_realisees': self.nombre_palettes_realisees,
            'status_class': self.status_class,
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

commandes_par_calibre = {}
commandes_par_calibre = charger_commandes('commandes.json')
    
@app.route('/')
def accueil():
    volume = 0
    return render_template('accueil.html')

@app.route('/maj-commandes', methods=['GET', 'POST'])
def maj_commandes():
    volume = 0
    global checkbox_states
    if request.method == 'POST':
        nom = request.form['nom']
        calibre = calibres[request.form['calibre']]
        nombre_palettes = int(request.form['nombre_palettes'])
        
        
        nouvelle_commande = Commande(nom, calibre, nombre_palettes)
        commandes_par_calibre[calibre.nom].append(nouvelle_commande)

        # Émettre la mise à jour des commandes à tous les clients via SocketIO
        commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
        socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
        sauvegarder_commandes()

        return redirect(url_for('maj_commandes'))

    return render_template('maj_commandes.html', calibres=calibres, commandes_par_calibre=commandes_par_calibre)

@app.route('/reset', methods=['GET', 'POST'])
def reset():
    #remettre toutes les commande de bois a 0
    for commande in commandes_par_calibre.values():
        for cmd in commande:
            if cmd.nom == "Bois" or cmd.nom == "bois" or cmd.nom == "BOIS":
                cmd.nombre_palettes_realisees = 0
                cmd.nombre_colis = ""
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
    sauvegarder_commandes()
    return render_template('maj_commandes.html', calibres=calibres, commandes_par_calibre=commandes_par_calibre)

@app.route('/ajouter-commande', methods=['GET', 'POST'])
def ajouter_commande():
    volume = 0
    if request.method == 'POST':
        nom = request.form['nom']
        calibre = calibres[request.form['calibre']]
        nombre_palettes = int(request.form['nombre_palettes'])
        nombre_colis = int(request.form['nombre_colis'])
        id = generate_unique_id()
        
        nouvelle_commande = Commande(id, nom, calibre, nombre_palettes, nombre_colis)
        commandes_par_calibre[calibre.nom].append(nouvelle_commande)

        # Émettre la mise à jour des commandes à tous les clients via SocketIO
        commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
        socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
        sauvegarder_commandes()

        return redirect(url_for('maj_commandes'))

    return render_template('ajouter_commande.html', calibres=calibres)

@app.route('/liste-commandes')
def liste_commandes():
    volume = 0
    return render_template('liste_commandes.html', commandes_par_calibre=commandes_par_calibre)

@app.route('/incrementer-palettes/<string:commande_id>')
def incrementer_palettes(commande_id):
    volume = 0
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                cmd.nombre_palettes_realisees += 1
                if cmd.nombre_palettes - cmd.nombre_palettes_realisees == 1:
                    socketio.emit('volume_notification', {'volume': volume})
                break

    # Émettre la mise à jour des commandes à tous les clients via SocketIO
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
    sauvegarder_commandes()

    return redirect(url_for('maj_commandes'))

@app.route('/decrementer-palettes/<string:commande_id>')
def decrementer_palettes(commande_id):
    volume = 0
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id and cmd.nombre_palettes_realisees > 0:
                cmd.nombre_palettes_realisees -= 1
                break

    # Émettre la mise à jour des commandes à tous les clients via SocketIO
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
    sauvegarder_commandes()

    return redirect(url_for('maj_commandes'))

@app.route('/valide-colis/<string:commande_id>')
def valide_colis(commande_id):
    volume = 0
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id :
                if cmd.nombre_colis != "" :
                    if str(cmd.nombre_colis)[-1] != ")" :
                        cmd.nombre_colis = str(cmd.nombre_colis) + " (Terminé)"
                break

    # Émettre la mise à jour des commandes à tous les clients via SocketIO
    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
    sauvegarder_commandes()

    return redirect(url_for('maj_commandes'))



@app.route('/modifier-commande/<string:commande_id>', methods=['GET', 'POST'])
def modifier_commande(commande_id):
    volume = 0
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                if request.method == 'POST':
                    cmd.nom = request.form['nom']
                    cmd.nombre_palettes = int(request.form['nombre_palettes'])
                    if int(request.form['nombre_colis']) > 0 :
                        cmd.nombre_colis = "|| Colis : " + str(int(request.form['nombre_colis']))
                    else :
                        cmd.nombre_colis = ""
                    # Émettre la mise à jour des commandes à tous les clients via SocketIO
                    commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
                    socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
                    sauvegarder_commandes()

                    return redirect(url_for('maj_commandes'))

                return render_template('modifier_commande.html', calibres=calibres, commande=cmd)

    return redirect(url_for('maj_commandes'))

@app.route('/supprimer-commande/<string:commande_id>')
def supprimer_commande(commande_id):
    volume = 0
    for calibre, commandes in commandes_par_calibre.items():
        for cmd in commandes:
            if cmd.id == commande_id:
                commandes.remove(cmd)
                # Émettre la mise à jour des commandes à tous les clients via SocketIO
                commandes_dict = {calibre: [cmd.to_dict() for cmd in commandes] for calibre, commandes in commandes_par_calibre.items()}
                socketio.emit('mise_a_jour_commande', {'commandes': commandes_dict})
                break
    sauvegarder_commandes()
    return redirect(url_for('maj_commandes'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
