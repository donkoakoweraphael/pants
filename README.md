# PANT — Plateforme d'Administration et Numérisation Terrain

Bienvenue sur le dépôt du projet **PANT**. Ce guide détaille pas à pas l'ensemble des étapes nécessaires pour cloner, configurer, initialiser et exécuter le projet, que ce soit **avec Docker** (environnement conteneurisé standardisé) ou **sans Docker** (environnement virtuel Python local direct).

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Étape 1 : Clonage du Dépôt](#2-étape-1--clonage-du-dépôt)
3. [Étape 2 : Configuration des Variables d'Environnement](#3-étape-2--configuration-des-variables-denvironnement)
4. [Méthode A : Démarrage AVEC Docker (Recommandé)](#4-méthode-a--démarrage-avec-docker-recommandé)
   - [A.1. Lancement des conteneurs](#a1-lancement-des-conteneurs)
   - [A.2. Application des migrations](#a2-application-des-migrations)
   - [A.3. Création du compte administrateur (Superuser)](#a3-création-du-compte-administrateur-superuser)
   - [A.4. Exécution de la suite de tests](#a4-exécution-de-la-suite-de-tests)
   - [A.5. Commandes utiles au quotidien](#a5-commandes-utiles-au-quotidien)
5. [Méthode B : Démarrage SANS Docker (Environnement Local)](#5-méthode-b--démarrage-sans-docker-environnement-local)
   - [B.1. Création de l'environnement virtuel](#b1-création-de-lenvironnement-virtuel)
   - [B.2. Activation de l'environnement virtuel](#b2-activation-de-lenvironnement-virtuel)
   - [B.3. Installation des dépendances](#b3-installation-des-dépendances)
   - [B.4. Configuration de la base de données locale](#b4-configuration-de-la-base-de-données-locale)
   - [B.5. Application des migrations](#b5-application-des-migrations)
   - [B.6. Création du compte administrateur](#b6-création-du-compte-administrateur)
   - [B.7. Exécution des tests](#b7-exécution-des-tests)
   - [B.8. Démarrage du serveur de développement](#b8-démarrage-du-serveur-de-développement)
6. [Points d'Accès et Documentation](#6-points-daccès-et-documentation)
7. [Dépannage & Bonnes Pratiques](#7-dépannage--bonnes-pratiques)

---

## 1. Prérequis

Avant de commencer, assurez-vous d'avoir installé sur votre machine :

| Outil | Version recommandée | Remarques |
| :--- | :--- | :--- |
| **Git** | $\ge$ 2.40 | Présent nativement sous Linux/macOS, téléchargeable via [git-scm.com](https://git-scm.com/) pour Windows |
| **Docker & Docker Compose** | Docker 24+ / Compose v2+ | **Obligatoire uniquement pour la méthode avec Docker** ([Docker Desktop](https://www.docker.com/products/docker-desktop/) sous Windows/macOS) |
| **Python** | 3.12 | **Obligatoire uniquement pour la méthode sans Docker** (avec `pip` et `venv`) |

---

## 2. Étape 1 : Clonage du Dépôt

Ouvrez votre terminal et clonez le dépôt Git du projet, puis placez-vous dans le répertoire de travail :

### Linux / macOS / Windows (Git Bash)
```bash
git clone <URL_DU_DEPOT> PANT
cd PANT
```

### Windows (PowerShell)
```powershell
git clone <URL_DU_DEPOT> PANT
Set-Location PANT
```

### Windows (Invite de commandes CMD)
```cmd
git clone <URL_DU_DEPOT> PANT
cd PANT
```

---

## 3. Étape 2 : Configuration des Variables d'Environnement

Le projet lit sa configuration depuis un fichier `.env`. Un modèle prêt à l'emploi [`.env.example`](.env.example) est fourni à la racine.

Copiez le fichier d'exemple vers un fichier `.env` :

### Linux / macOS / Windows (Git Bash)
```bash
cp .env.example .env
```

### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
```

### Windows (Invite de commandes CMD)
```cmd
copy .env.example .env
```

> **Note :** 
> - **Sous Docker** : Les variables `POSTGRES_*` sont lues automatiquement pour initialiser la base PostgreSQL dans le conteneur `pant_postgres_db`.
> - **Hors Docker** : Le fichier d'exemple configure par défaut `DATABASE_URL=sqlite:///db.sqlite3` pour vous permettre de travailler immédiatement sans avoir à installer de serveur PostgreSQL en local.

---

## 4. Méthode A : Démarrage AVEC Docker (Recommandé)

Cette méthode instancie l'ensemble de la pile conteneurisée :
- Le serveur d'application Django Ninja (**`pant_django_web`**)
- La base de données PostgreSQL 16 (**`pant_postgres_db`**)
- Le volume persistant (**`pant_postgres_data`**)
- Le réseau applicatif (**`pant_network`**)

### A.1. Lancement des conteneurs

Cette commande construit l'image applicative `pant_django_web:latest` et démarre les services en arrière-plan :

#### Linux / macOS / Windows (tous terminaux : PowerShell, CMD, Git Bash)
```bash
docker compose up -d --build
```

Pour vérifier que les conteneurs sont bien démarrés et sains :
```bash
docker compose ps
```

---

### A.2. Application des migrations

Une fois PostgreSQL prêt (healthcheck validé), appliquez les migrations de base de données :

#### Linux / macOS / Windows (tous terminaux)
```bash
docker compose exec web python manage.py migrate
```

---

### A.3. Création du compte administrateur (Superuser)

Créez le superutilisateur initial pour accéder à l'interface d'administration Django :

#### Linux / macOS / Windows (PowerShell ou CMD)
```bash
docker compose exec web python manage.py createsuperuser
```

#### Windows (Git Bash)
> En cas de blocage d'interactivité sous Git Bash, préfixez la commande avec `winpty` :
```bash
winpty docker compose exec web python manage.py createsuperuser
```

Renseignez l'adresse email, le prénom, le nom et le mot de passe lorsque vous y êtes invité.

---

### A.4. Exécution de la suite de tests

Pour vérifier l'intégrité de l'application et la conformité des endpoints sur PostgreSQL :

#### Linux / macOS / Windows (tous terminaux)
```bash
docker compose exec web python manage.py test accounts core -v 2
```

---

### A.5. Commandes utiles au quotidien

| Action souhaitée | Commande à exécuter |
| :--- | :--- |
| **Consulter les logs applicatifs en direct** | `docker compose logs -f web` |
| **Consulter les logs de la base de données** | `docker compose logs -f db` |
| **Ouvrir un shell interactif Django** | `docker compose exec web python manage.py shell` |
| **Ouvrir un terminal Bash dans le conteneur web** | `docker compose exec web bash` |
| **Arrêter temporairement les conteneurs** | `docker compose stop` |
| **Redémarrer les conteneurs** | `docker compose start` |
| **Arrêter et supprimer les conteneurs et réseaux** | `docker compose down` |
| **Remise à zéro complète (suppression des conteneurs ET des volumes de données)** | `docker compose down -v` |

---

## 5. Méthode B : Démarrage SANS Docker (Environnement Local)

Cette méthode exécute Django directement sur la machine hôte.

### B.1. Création de l'environnement virtuel

Créez un environnement virtuel isolé nommé `.venv` à la racine du projet :

#### Linux / macOS
```bash
python3 -m venv .venv
```

#### Windows (PowerShell, CMD ou Git Bash)
```powershell
python -m venv .venv
```
*(Si plusieurs versions de Python sont installées sur Windows, forcez Python 3.12 via : `py -3.12 -m venv .venv`)*

---

### B.2. Activation de l'environnement virtuel

Activez l'environnement virtuel selon votre système d'exploitation et votre shell :

#### Linux / macOS (Bash / Zsh)
```bash
source .venv/bin/activate
```

#### Windows (PowerShell)
```powershell
.venv\Scripts\Activate.ps1
```
> **Astuce PowerShell :** Si une erreur de restriction de script apparaît (*"l'exécution de scripts est désactivée sur ce système"*), débloquez la session avec :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### Windows (Invite de commandes CMD)
```cmd
.venv\Scripts\activate.bat
```

#### Windows (Git Bash)
```bash
source .venv/Scripts/activate
```

*(Votre invite de commande doit afficher le préfixe `(.venv)`)*.

---

### B.3. Installation des dépendances

Mettez à jour le gestionnaire de paquets `pip` puis installez les dépendances déclarées :

#### Tous systèmes (Linux / macOS / Windows)
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### B.4. Configuration de la base de données locale

Ouvrez votre fichier `.env` local. Par défaut, pour une exécution locale sans dépendance externe :
```env
DATABASE_URL=sqlite:///db.sqlite3
```
Si vous disposez d'un serveur PostgreSQL local, vous pouvez renseigner votre URL de connexion :
```env
DATABASE_URL=postgres://mon_user:mon_mot_de_passe@localhost:5432/pant_db
```

---

### B.5. Application des migrations

Initialisez le schéma de base de données :

#### Tous systèmes (Linux / macOS / Windows)
```bash
python manage.py migrate
```

---

### B.6. Création du compte administrateur

Créez votre compte superutilisateur :

#### Tous systèmes (Linux / macOS / Windows)
```bash
python manage.py createsuperuser
```

---

### B.7. Exécution des tests

Validez la suite de tests sur l'environnement local :

#### Tous systèmes (Linux / macOS / Windows)
```bash
python manage.py test accounts core -v 2
```

---

### B.8. Démarrage du serveur de développement

Lancez le serveur HTTP Django :

#### Tous systèmes (Linux / macOS / Windows)
```bash
python manage.py runserver
```

Le serveur écoute par défaut sur `http://127.0.0.1:8000/`.

---

## 6. Points d'Accès et Documentation

Une fois le serveur en ligne (que ce soit via **Docker** ou en **local**), vous avez accès aux interfaces suivantes :

| Interface | URL | Description |
| :--- | :--- | :--- |
| **Documentation Swagger UI** | [http://localhost:8000/api/docs](http://localhost:8000/api/docs) | Interface interactive officielle pour tester tous les endpoints REST Ninja |
| **Documentation Redoc** | [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc) | Documentation alternative au format Redoc |
| **Schéma OpenAPI JSON** | [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json) | Spécification brute OpenAPI 3.0 téléchargeable |
| **Administration Django** | [http://localhost:8000/admin/](http://localhost:8000/admin/) | Back-office d'administration Django |
| **Endpoint de Santé** | [http://localhost:8000/api/health](http://localhost:8000/api/health) | Endpoint de vérification de l'état du service (liveness probe) |

---

## 7. Dépannage & Bonnes Pratiques

### 1. Conflit de port `8000` ou `5432`
Si le port `8000` (web) ou `5432` (PostgreSQL) est déjà utilisé par une autre application :
- Dans votre fichier `.env`, vous pouvez modifier `POSTGRES_PORT=5433` par exemple.
- Pour changer le port web hors Docker : `python manage.py runserver 8080`.
- Pour changer le port web sous Docker, ajustez le mapping dans `docker-compose.yml` : `"8080:8000"`.

### 2. Réinitialisation complète de l'environnement Docker
Si vous souhaitez réinitialiser entièrement la base PostgreSQL sous Docker :
```bash
docker compose down -v
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

### 3. Fichier `.env` sous Git
Le fichier `.env` contient des secrets et est ignoré par Git via le [`.gitignore`](.gitignore). **Ne le committez jamais sur le dépôt.**
