# AI Agent

Un agent IA minimal en Python, prêt à discuter en ligne de commande avec le modèle OpenAI de ton choix.

## Fonctionnalités

- Chat interactif en terminal
- Mémoire de conversation locale pendant la session
- Prompt système personnalisable
- Configuration simple via `.env`
- Mode Google Forms pour proposer ou préremplir des réponses
- Interface web flottante avec switch on/off et boîte déplaçable
- Site statique de téléchargement prêt pour GitHub Pages

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
cp .env.example .env
```

Ensuite, ajoute ta clé API dans `.env`.

## Lancement

```bash
python3 agent.py
```

## Interface Web

Pour lancer l'agent dans une boîte web déplaçable :

```bash
python3 web_agent.py
```

Puis ouvre [http://127.0.0.1:8000](http://127.0.0.1:8000).

L'interface inclut :

- une boîte d'agent draggable en cliquant sur l'en-tête
- un switch `on/off`
- un fond gris foncé translucide à environ 50%
- un champ de chat relié à l'API OpenAI

## Site Downloader

Le dossier [docs/index.html](/Users/isaac/Documents/codex/hack.../ai%20agent/docs/index.html) contient un site statique prêt à pousser sur GitHub.

Fichiers principaux :

- [docs/index.html](/Users/isaac/Documents/codex/hack.../ai%20agent/docs/index.html)
- [docs/styles.css](/Users/isaac/Documents/codex/hack.../ai%20agent/docs/styles.css)
- [docs/script.js](/Users/isaac/Documents/codex/hack.../ai%20agent/docs/script.js)

Pour l'utiliser :

1. pousse le repo sur GitHub
2. active GitHub Pages avec la source `main` et le dossier `docs`
3. remplace les URLs de téléchargement dans `docs/script.js`

Le site inclut :

- une page de téléchargement responsive
- des cartes Windows, macOS et Linux
- une boîte flottante déplaçable avec switch `on/off`
- un fond sombre et une mise en page déjà prête pour une release

## Google Forms

Le projet inclut aussi un script pour lire un Google Form, demander au modèle de préparer des réponses, puis préremplir le formulaire.

### Prévisualiser les réponses

```bash
python3 google_forms_agent.py "https://docs.google.com/forms/..."
```

### Préremplir le formulaire sans l'envoyer

```bash
python3 google_forms_agent.py "https://docs.google.com/forms/..." --fill
```

### Préremplir puis soumettre

```bash
python3 google_forms_agent.py "https://docs.google.com/forms/..." --fill --submit
```

### Donner du contexte à l'agent

```bash
python3 google_forms_agent.py "https://docs.google.com/forms/..." \
  --fill \
  --context "Je suis étudiant en informatique, je préfère le distanciel et je suis disponible le samedi."
```

### Limites

- Certains formulaires demandent une connexion Google manuelle.
- Les types de questions complexes peuvent nécessiter un ajustement.
- Le script ne soumet pas le formulaire par défaut.

## Commandes utiles

- `/reset` : vide l'historique de la conversation
- `/system ...` : change le prompt système à la volée
- `/quit` : quitte le programme

## Variables d'environnement

- `OPENAI_API_KEY` : ta clé API OpenAI
- `OPENAI_MODEL` : modèle à utiliser, par défaut `gpt-4.1-mini`
- `OPENAI_SYSTEM_PROMPT` : prompt système initial

## Exemple

```text
Tu > aide-moi à écrire un script Python
Agent > Bien sûr. Quel est l'objectif du script ?
```

## Google Forms au clic

Le fichier [google_forms_click_assistant.user.js](/Users/isaac/Documents/codex/ai%20agent/google_forms_click_assistant.user.js) ajoute un mode interactif pour Google Forms.

Fonctionnement :

- lance d'abord `python3 web_agent.py`
- installe le userscript dans Tampermonkey
- ouvre un Google Form
- active le switch dans la petite boîte
- clique sur une question pour que l'agent la remplisse

Le script utilise le contexte saisi dans la boîte pour répondre de façon cohérente.
