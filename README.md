# 🌞 Google Ads MCP — Connecter Claude à Google Ads

> Donnez à Claude un accès direct à votre compte Google Ads. Analysez les campagnes, optimisez les enchères, ajoutez des mots-clés négatifs et générez des rapports — depuis une interface de chat.

Créé par **Anthony Bressy** • [Lire l'article complet](https://influenci.com/blog/connecter-claude-google-ads)

---

## Ce que ça fait

Une fois connecté, Claude peut de manière autonome :

- 📊 **Analyser** la performance des campagnes, mots-clés et termes de recherche
- ⏸ **Mettre en pause** les mots-clés non performants
- 💰 **Modifier les enchères** sur n'importe quel mot-clé
- 🚫 **Ajouter des mots-clés négatifs** au niveau campagne ou compte (listes partagées)
- 📈 **Générer des rapports** (Word, Excel) avec recommandations d'expert

### Exemples de prompts

```
"Analyse les 30 derniers jours. Quels mots-clés gaspillent du budget ?"
"Mets en pause les mots-clés à 0 impression et monte l'enchère sur 'installateur photovoltaïque Corse' à 7€"
"Crée un rapport d'audit complet avec un plan de recommandations sur 90 jours"
"Ajoute EDF, ANAH, Oreli comme mots-clés négatifs sur toutes les campagnes"
```

---

## Architecture

```
Claude.ai ←→ ngrok (tunnel HTTPS) ←→ Serveur MCP (local) ←→ Google Ads API
```

Le serveur MCP tourne en local sur votre machine. Vos credentials ne quittent jamais votre ordinateur.

---

## Outils disponibles

| Outil | Description |
|-------|-------------|
| `get_campaigns` | Performance des campagnes (N jours) |
| `get_keywords` | Mots-clés avec enchères |
| `get_search_terms` | Requêtes réelles déclenchant vos annonces |
| `get_ads` | Annonces actives et leurs métriques |
| `get_budget_overview` | Budget et dépenses par campagne |
| `pause_keyword` | Mettre en pause un mot-clé |
| `update_keyword_bid` | Modifier l'enchère CPC max |
| `add_negative_keywords_to_campaign` | Ajouter des négatifs à une campagne |
| `add_negative_keywords_to_account` | Créer une liste partagée appliquée à toutes les campagnes |
| `get_negative_keywords` | Lister les mots-clés négatifs existants |

---

## Prérequis

- Python 3.12+
- Un **compte Google Ads Manager (MCC)**
- Un projet Google Cloud avec l'API Google Ads activée
- Un compte [ngrok](https://ngrok.com) (gratuit)
- Un compte [Claude.ai](https://claude.ai) (Pro ou Team)

---

## Installation étape par étape

### Étape 1 — Créer un compte Google Ads Manager (MCC)

Le compte Manager est indispensable — c'est lui qui donne accès à l'API Google Ads.

1. Rendez-vous sur [ads.google.com/home/tools/manager-accounts](https://ads.google.com/home/tools/manager-accounts)
2. Cliquez **"Créer un compte Manager"**
3. Une fois créé, liez votre compte client : **Comptes → Résumé → "+"**

### Étape 2 — Obtenir le Developer Token

1. Connectez-vous à votre **compte Manager** sur [ads.google.com](https://ads.google.com)
2. Allez dans **Admin → Centre API**
3. Remplissez le formulaire (email, nom entreprise, type : Agence/SEM)
4. Soumettez → Google vous délivre immédiatement votre **Developer Token**
5. Copiez-le, vous en aurez besoin dans `config.json`

> ⚠️ Le Developer Token doit être créé depuis le compte **Manager**, pas depuis un compte publicitaire classique.

### Étape 3 — Créer les credentials OAuth sur Google Cloud

1. Rendez-vous sur [console.cloud.google.com](https://console.cloud.google.com)
2. Cliquez **"Nouveau projet"** → nommez-le "Google Ads MCP"
3. Dans le menu gauche : **APIs & Services → Bibliothèque**
4. Recherchez **"Google Ads API"** → cliquez **Activer**
5. Dans le menu gauche : **APIs & Services → Identifiants**
6. Cliquez **"Créer des identifiants" → "ID client OAuth 2.0"**
7. Type d'application : **"Application de bureau"**
8. Cliquez **Créer**
9. Copiez le **Client ID** et le **Client Secret** affichés

### Étape 4 — Installer Python et cloner le repo

**Installer Homebrew et Python 3.12 (Mac) :**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12
```

**Cloner le repo :**
```bash
git clone https://github.com/ab-solution-dev/google-ads-mcp.git
cd google-ads-mcp
```

**Créer l'environnement virtuel et installer les dépendances :**
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install google-ads google-auth-oauthlib "mcp[cli]" starlette uvicorn
```

### Étape 5 — Configurer les credentials

Copiez le fichier template :
```bash
cp config.example.json config.json
```

Ouvrez `config.json` et remplissez vos valeurs :
```json
{
  "developer_token": "VOTRE_DEVELOPER_TOKEN",
  "client_id": "VOTRE_CLIENT_ID.apps.googleusercontent.com",
  "client_secret": "VOTRE_CLIENT_SECRET",
  "refresh_token": "",
  "customer_id": "ID_COMPTE_CLIENT_SANS_TIRETS",
  "login_customer_id": "ID_COMPTE_MANAGER_SANS_TIRETS"
}
```

**Où trouver chaque valeur :**

| Champ | Où le trouver |
|-------|--------------|
| `developer_token` | Google Ads Manager → Admin → Centre API |
| `client_id` | Google Cloud Console → APIs & Services → Identifiants → OAuth 2.0 |
| `client_secret` | Google Cloud Console → APIs & Services → Identifiants → OAuth 2.0 |
| `refresh_token` | Généré automatiquement à l'étape 6 |
| `customer_id` | ID du compte Google Ads client, visible en haut à droite (sans tirets, ex: 1234567890) |
| `login_customer_id` | ID de votre compte Manager (sans tirets, ex: 3341610533) |

### Étape 6 — Générer le refresh token (une seule fois)

```bash
source venv/bin/activate
python setup.py
```

Un navigateur s'ouvre → connectez-vous avec le compte Google lié à Google Ads → autorisez l'accès. Le refresh token est sauvegardé automatiquement dans `config.json`.

### Étape 7 — Lancer le serveur MCP

```bash
source venv/bin/activate
python server.py
```

Vous devez voir :
```
Serveur MCP Google Ads démarré sur http://localhost:8080/sse
```

### Étape 8 — Installer ngrok et créer le tunnel HTTPS

Claude.ai exige du HTTPS. ngrok crée un tunnel sécurisé entre Internet et votre serveur local.

**Installer ngrok :**
```bash
brew install ngrok
```

**Créer un compte gratuit** sur [dashboard.ngrok.com/signup](https://dashboard.ngrok.com/signup)

**Récupérer votre authtoken** sur [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)

**Configurer et lancer ngrok (dans un nouveau terminal) :**
```bash
ngrok config add-authtoken VOTRE_TOKEN_NGROK
ngrok http 8080
```

Copiez l'URL affichée : `https://xxxx.ngrok-free.app`

> 💡 Sur le plan gratuit avec compte vérifié, l'URL reste stable entre les sessions.

### Étape 9 — Connecter à Claude.ai

1. Allez dans **Claude.ai → Paramètres → Connecteurs**
2. Cliquez **"Ajouter un connecteur personnalisé"**
3. Entrez l'URL : `https://xxxx.ngrok-free.app/sse`
4. Sauvegardez → le connecteur passe au vert ✅

---

## Lancement rapide (double-clic)

Pour ne plus avoir à ouvrir deux terminaux à chaque fois :

```bash
chmod +x lancer_mcp.sh
```

Dans le Finder, faites clic droit sur `lancer_mcp.sh` → **"Ouvrir avec" → Terminal**. Un double-clic suffit ensuite pour lancer les deux serveurs simultanément.

---

## Sécurité

- `config.json` contient vos credentials — **il est dans `.gitignore` et ne sera jamais commité**
- Le serveur MCP ne tourne que lorsque le script est actif
- ngrok ne nécessite pas d'ouverture de port permanente
- Claude.ai n'accède qu'aux données via les outils explicitement définis

---

## Roadmap

- [ ] Créer des campagnes depuis Claude
- [ ] Créer et modifier des annonces RSA
- [ ] Rapports de performance hebdomadaires automatiques par email
- [ ] Support des campagnes Performance Max
- [ ] Support multi-comptes

---

## Licence

Open source — libre d'utilisation, modification et distribution.

---

**Anthony Bressy** — [bressy.anthony@gmail.com](mailto:bressy.anthony@gmail.com)
