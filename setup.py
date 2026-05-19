#!/usr/bin/env python3
"""
setup.py — Installation + génération du refresh_token
Lance ce script UNE SEULE FOIS avant de démarrer le serveur MCP.
"""

import subprocess
import sys
import json
from pathlib import Path

CONFIG_PATH = Path.home() / "Documents" / "googleads-mcp" / "config.json"

def install_deps():
    print("📦 Installation des dépendances...")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
        "google-ads", "google-auth-oauthlib", "mcp"])
    print("✅ Dépendances installées\n")

def generate_refresh_token():
    from google_auth_oauthlib.flow import InstalledAppFlow

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    if cfg["refresh_token"] != "COLLE_TON_REFRESH_TOKEN_ICI":
        print("✅ Refresh token déjà configuré, on passe.\n")
        return

    print("🔐 Génération du refresh_token...")
    print("   → Un navigateur va s'ouvrir, connecte-toi avec ton compte Google Ads\n")

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id":      cfg["client_id"],
                "client_secret":  cfg["client_secret"],
                "redirect_uris":  ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                "auth_uri":       "https://accounts.google.com/o/oauth2/auth",
                "token_uri":      "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/adwords"]
    )
    credentials = flow.run_local_server(port=0)

    # Mise à jour du config.json
    cfg["refresh_token"] = credentials.refresh_token
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

    print(f"\n✅ Refresh token sauvegardé dans {CONFIG_PATH}")

def check_required(cfg, fields):
    missing = [k for k in fields if "COLLE" in str(cfg.get(k,"")) or "ID_COMPTE" in str(cfg.get(k,"")) or not cfg.get(k,"")]
    if missing:
        print(f"⚠️  Champs manquants dans config.json : {', '.join(missing)}")
        print(f"   → Ouvre {CONFIG_PATH} et remplis ces valeurs\n")
        sys.exit(1)

def ask_missing(cfg):
    """Demande interactivement les champs manquants non critiques."""
    changed = False

    if not cfg.get("customer_id") or "ID_COMPTE" in cfg["customer_id"]:
        val = input("👉 customer_id ATEA (ID compte sans tirets, ex: 1234567890) : ").strip()
        cfg["customer_id"] = val
        changed = True

    if not cfg.get("login_customer_id") or "ID_COMPTE" in cfg["login_customer_id"]:
        val = input("👉 login_customer_id Manager (sans tirets, ex: 3341610533) : ").strip()
        cfg["login_customer_id"] = val
        changed = True

    if changed:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
        print("✅ config.json mis à jour\n")

    return cfg

if __name__ == "__main__":
    print("=" * 55)
    print("  ATEA Google Ads MCP — Setup")
    print("=" * 55 + "\n")

    install_deps()

    with open(CONFIG_PATH) as f:
        cfg = json.load(f)

    # 1. Vérifie les champs critiques pour OAuth
    check_required(cfg, ["developer_token", "client_id", "client_secret"])

    # 2. Génère le refresh_token si manquant
    generate_refresh_token()

    # 3. Demande les IDs manquants interactivement
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    ask_missing(cfg)

    print("\n🚀 Setup terminé ! Pour lancer le serveur MCP :")
    print(f"   source ~/Documents/googleads-mcp/venv/bin/activate")
    print(f"   python ~/Documents/googleads-mcp/server.py")
    print("\nEnsuite connecte-le dans Claude.ai → Paramètres → Connecteurs")
