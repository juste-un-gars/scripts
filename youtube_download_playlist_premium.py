"""
================================================================================
    TÉLÉCHARGEUR DE PLAYLIST YOUTUBE - QUALITÉ PREMIUM
================================================================================

PRÉREQUIS À INSTALLER :
-----------------------

1. PYTHON (si pas déjà installé)
   → https://www.python.org/downloads/
   → Cocher "Add to PATH" lors de l'installation

2. YT-DLP (bibliothèque de téléchargement)
   → pip install -U yt-dlp

3. FFMPEG (pour fusionner vidéo + audio)
   → winget install ffmpeg
   → Ou télécharger depuis https://ffmpeg.org/download.html
   → Vérifier : ffmpeg -version

4. DENO (runtime JavaScript requis par YouTube)
   → winget install DenoLand.Deno
   → Ou PowerShell : irm https://deno.land/install.ps1 | iex
   → Redémarrer le terminal après installation
   → Vérifier : deno --version

5. COOKIES YOUTUBE (pour la qualité Premium)
   → Installer l'extension Chrome "Get cookies.txt LOCALLY"
     https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
   → Aller sur youtube.com (connecté avec un compte Premium)
   → Cliquer sur l'extension → Export
   → Sauvegarder le fichier "cookies.txt" dans le même dossier que ce script

STRUCTURE DU DOSSIER :
----------------------
    D:\VIDEODOWNLOAD\
    ├── playlist.py      (ce script)
    ├── cookies.txt      (exporté depuis Chrome)
    └── downloads\       (créé automatiquement)
        ├── 01 - Titre vidéo 1.mp4
        ├── 02 - Titre vidéo 2.mp4
        └── ...

UTILISATION :
-------------
    python playlist.py

    Puis entrer l'URL de la playlist et le dossier de destination.
    Ctrl+C pour interrompre, relancer pour reprendre.

QUALITÉS TÉLÉCHARGÉES (par ordre de priorité) :
-----------------------------------------------
    1. 1080p50 Premium (meilleur bitrate, compte Premium requis)
    2. 1080p50 standard
    3. 1080p50 VP9
    4. Meilleure qualité disponible

DÉPANNAGE :
-----------
    "No supported JavaScript runtime" → Installer Deno (étape 4)
    "n challenge solving failed"      → Ajouter --remote-components ejs:github
    "Requested format not available"  → Vérifier cookies.txt / compte Premium
    "Failed to decrypt DPAPI"         → Utiliser cookies.txt au lieu du navigateur
    Fichiers .part restants           → Téléchargement interrompu, relancer

================================================================================
"""

import yt_dlp
import sys
import os


def download_playlist(playlist_url, output_folder="./downloads"):
    os.makedirs(output_folder, exist_ok=True)
    
    options = {
        # Format Premium : 1080p50 Premium + meilleur audio, avec fallbacks
        'format': '721+140/299+140/303+251/bv*+ba/b',
        
        # Nom de fichier : "01 - Titre.mp4"
        'outtmpl': f'{output_folder}/%(playlist_index)02d - %(title)s.%(ext)s',
        
        # Compatibilité Windows (caractères spéciaux)
        'windowsfilenames': True,
        
        # Fusion en MP4
        'merge_output_format': 'mp4',
        
        # Cookies pour accès Premium
        'cookiefile': 'cookies.txt',
        
        # Résolution du challenge JavaScript YouTube
        'remote_components': ['ejs:github'],
        
        # Robustesse réseau
        'ignoreerrors': True,
        'retries': 10,
        'fragment_retries': 10,
        
        # Ne pas re-télécharger les fichiers existants
        'nooverwrites': True,
        
        # Affichage
        'progress_hooks': [on_progress],
        'quiet': False,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(options) as ydl:
        print(f"\n📋 Analyse de la playlist...")
        ydl.download([playlist_url])


def on_progress(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', '')
        print(f"\r  ⬇️  {percent} à {speed} (reste: {eta})      ", end='', flush=True)
    elif d['status'] == 'finished':
        title = d.get('info_dict', {}).get('title', 'Vidéo')
        print(f"\n  ✅ {title}")


if __name__ == "__main__":
    print("=" * 60)
    print("       TÉLÉCHARGEUR PLAYLIST YOUTUBE PREMIUM")
    print("=" * 60)
    
    # Vérification cookies
    if not os.path.exists('cookies.txt'):
        print("\n⚠️  cookies.txt introuvable !")
        print("   → Qualité Premium non disponible")
        print("   → Voir instructions en haut du script")
        response = input("\nContinuer quand même ? (o/N) : ").strip().lower()
        if response != 'o':
            sys.exit(1)
    else:
        print("\n✅ cookies.txt détecté - Qualité Premium activée")
    
    # URL
    url = input("\n🔗 URL de la playlist ou vidéo : ").strip()
    if not url:
        print("❌ Aucune URL fournie.")
        sys.exit(1)
    
    # Dossier de destination
    output = input("📁 Dossier de destination (Entrée = ./downloads) : ").strip()
    if not output:
        output = "./downloads"
    
    # Lancement
    print(f"\n🚀 Téléchargement vers : {output}")
    print("🎬 Qualité : 1080p50 Premium (si disponible)")
    print("💡 Ctrl+C pour arrêter, relancez pour reprendre\n")
    
    try:
        download_playlist(url, output)
        print("\n" + "=" * 60)
        print("✅ Téléchargement terminé !")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⏸️  Interrompu. Relancez pour reprendre.")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
