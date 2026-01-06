#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image
from io import BytesIO
from urllib.parse import urljoin

print("📚 Convertisseur Web → EPUB")
print("=" * 50)

# =====================================================
# ENTRÉES UTILISATEUR
# =====================================================
url = input("➡️  URL de la page : ").strip()
if not url:
    print("❌ URL obligatoire")
    exit(1)

cover_url = input("🖼️  URL de la couverture (optionnel) : ").strip()

# =====================================================
# TÉLÉCHARGEMENT DE LA PAGE
# =====================================================
print("🌐 Téléchargement de la page...")
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
except Exception as e:
    print(f"❌ Erreur : {e}")
    exit(1)

# Extraction du titre
title = "Sans titre"

# Essayer d'abord la balise <title>
title_tag = soup.find('title')
if title_tag:
    title = title_tag.get_text(strip=True)
    # Nettoyer le titre (souvent "Titre | Nom du site")
    if '|' in title:
        title = title.split('|')[0].strip()
    elif '–' in title:
        title = title.split('–')[0].strip()
    elif '-' in title and len(title.split('-')) == 2:
        title = title.split('-')[0].strip()

# Si pas de titre ou titre générique, essayer h1
if not title or title == "Sans titre":
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text(strip=True)

print(f"📖 Titre : {title}")

# Extraction du contenu
article = soup.find('div', class_='entry-content')
if not article:
    article = soup.find('article')
if not article:
    print("❌ Impossible de trouver le contenu")
    exit(1)

# =====================================================
# NOM DU FICHIER (après avoir récupéré le titre)
# =====================================================
# Nettoyer le titre pour en faire un nom de fichier valide
safe_title = title
for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
    safe_title = safe_title.replace(char, '-')

output = input(f"💾 Nom du fichier [{safe_title}] : ").strip()
if not output:
    output = safe_title
if not output.endswith('.epub'):
    output += '.epub'

print(f"\n⏳ Création de {output}...\n")

# =====================================================
# CRÉATION DE L'EPUB
# =====================================================
book = epub.EpubBook()
book.set_identifier(f'id{hash(url)}')
book.set_title(title)
book.set_language('fr')
book.add_author('Web')

# =====================================================
# CSS
# =====================================================
css = '''
body {
    font-family: serif;
    line-height: 1.6;
    margin: 2em;
}
h1 {
    font-size: 2em;
    margin-bottom: 1em;
}
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}
p {
    margin: 0.5em 0;
}
'''

css_file = epub.EpubItem(
    uid='style',
    file_name='style.css',
    media_type='text/css',
    content=css.encode('utf-8')
)
book.add_item(css_file)

# =====================================================
# COUVERTURE
# =====================================================
if cover_url:
    print(f"🖼️  Téléchargement de la couverture...")
    try:
        cover_response = requests.get(cover_url, timeout=30)
        cover_response.raise_for_status()
        
        # Conversion en PNG
        img = Image.open(BytesIO(cover_response.content))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionner si nécessaire
        if img.height > 1600:
            ratio = 1600 / img.height
            new_size = (int(img.width * ratio), 1600)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        cover_data = buffer.getvalue()
        
        # Méthode simple qui marche
        book.set_cover('cover.png', cover_data)
        
        print("✅ Couverture ajoutée")
    except Exception as e:
        print(f"⚠️  Erreur couverture : {e}")

# =====================================================
# IMAGES DE L'ARTICLE
# =====================================================
images = article.find_all('img')
print(f"📸 Traitement de {len(images)} images...")

for i, img_tag in enumerate(images):
    src = img_tag.get('src')
    if not src:
        continue
    
    # Normalisation de l'URL
    if src.startswith('//'):
        src = 'https:' + src
    elif src.startswith('/'):
        src = urljoin(url, src)
    elif not src.startswith('http'):
        src = urljoin(url, src)
    
    print(f"  [{i+1}/{len(images)}] {src[:50]}...")
    
    try:
        img_response = requests.get(src, timeout=20)
        img_response.raise_for_status()
        img_data = img_response.content
        
        # Conversion en JPEG
        try:
            img = Image.open(BytesIO(img_data))
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Redimensionner si trop large
            if img.width > 1200:
                ratio = 1200 / img.width
                new_size = (1200, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_data = buffer.getvalue()
        except:
            pass
        
        # Ajout au livre
        filename = f'images/img_{i}.jpg'
        img_item = epub.EpubItem(
            uid=f'img{i}',
            file_name=filename,
            media_type='image/jpeg',
            content=img_data
        )
        book.add_item(img_item)
        
        # Mise à jour du HTML
        img_tag['src'] = filename
        
    except Exception as e:
        print(f"    ⚠️  Erreur : {e}")

print(f"✅ Images traitées")

# =====================================================
# CHAPITRE HTML
# =====================================================
# Nettoyage
for tag in article.find_all(['script', 'style']):
    tag.decompose()

# Correction des balises auto-fermantes mal formées
# Convertir <br> en <br/>, <img> en <img/>, etc.
for br in article.find_all('br'):
    br.replace_with(soup.new_tag('br'))

for hr in article.find_all('hr'):
    hr.replace_with(soup.new_tag('hr'))

# Supprimer les attributs qui peuvent causer des problèmes
for tag in article.find_all(True):
    # Supprimer les attributs de style inline qui peuvent être mal formés
    if tag.has_attr('style'):
        del tag['style']
    # Supprimer les attributs de taille fixe
    if tag.name == 'img':
        for attr in ['width', 'height']:
            if tag.has_attr(attr):
                del tag[attr]

# Création du chapitre
# prettify() va formater correctement toutes les balises auto-fermantes
article_html = article.prettify()

html_content = f'''<html>
<head>
<title>{title}</title>
<link rel="stylesheet" href="style.css"/>
</head>
<body>
<h1>{title}</h1>
{article_html}
</body>
</html>'''

chapter = epub.EpubHtml(
    title=title,
    file_name='chapitre.xhtml',
    lang='fr'
)
chapter.set_content(html_content)
book.add_item(chapter)

# =====================================================
# STRUCTURE
# =====================================================
book.toc = (epub.Link('chapitre.xhtml', title, 'chap'),)
book.spine = ['nav', chapter]

book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# =====================================================
# EXPORT
# =====================================================
print(f"\n💾 Écriture du fichier...")
try:
    epub.write_epub(output, book, {})
    print(f"🎉 EPUB créé : {output}")
except Exception as e:
    print(f"❌ Erreur : {e}")
    exit(1)
