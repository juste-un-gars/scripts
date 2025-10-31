#!/usr/bin/env python3
"""
Script interactif : convertit une page Web en EPUB.

Il télécharge le contenu principal de la page,
intègre toutes les images localement,
et ajoute une couverture si tu fournis une URL.

Aucune dépendance supplémentaire par rapport à la version précédente.
"""

import re
import sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup, Comment
from ebooklib import epub

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; epub-generator/1.2; +mailto:you@example.com)"}


def fetch_url(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def clean_soup(soup):
    for s in soup(["script", "style", "noscript", "iframe", "nav", "aside", "footer", "header"]):
        s.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for selector in ["[class*=ad]", "[id*=ad]", "[class*=cookie]", "[id*=cookie]", ".share", ".social", ".meta"]:
        for node in soup.select(selector):
            node.decompose()


def extract_main_content(soup):
    article = soup.find("article")
    if article:
        return article
    main = soup.find("main")
    if main:
        return main
    candidates = soup.find_all(True, id=re.compile(r"(content|main|article|post)", re.I))
    if candidates:
        return max(candidates, key=lambda t: len(t.get_text(" ", strip=True)))
    return soup.body or soup


def get_meta(soup, name):
    tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
    return tag["content"].strip() if tag and tag.get("content") else None


def download_and_embed_images(soup, base_url, book):
    for idx, img in enumerate(soup.find_all("img"), 1):
        src = img.get("src")
        if not src:
            img.decompose()
            continue
        abs_url = urljoin(base_url, src)
        try:
            r = fetch_url(abs_url)
            data = r.content
            ext = "jpg"
            parsed = urlparse(abs_url)
            if "." in parsed.path:
                ext = parsed.path.split(".")[-1].split("?")[0].lower()
                if ext not in ["jpg", "jpeg", "png", "gif", "webp"]:
                    ext = "jpg"
            fname = f"image_{idx}.{ext}"
            img_item = epub.EpubItem(
                uid=f"img_{idx}",
                file_name=f"images/{fname}",
                media_type=f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}",
                content=data,
            )
            book.add_item(img_item)
            img["src"] = f"images/{fname}"
        except Exception as e:
            print(f"⚠️  Impossible de télécharger {abs_url}: {e}")
            img.decompose()


def build_epub(url, cover_url, output_filename):
    page = fetch_url(url)
    soup = BeautifulSoup(page.text, "lxml")

    title = (
        get_meta(soup, "og:title")
        or get_meta(soup, "twitter:title")
        or (soup.title.string.strip() if soup.title else "Sans titre")
    )
    author = get_meta(soup, "author") or get_meta(soup, "article:author") or "Inconnu"
    pubdate = get_meta(soup, "article:published_time") or get_meta(soup, "og:updated_time") or ""

    clean_soup(soup)
    content_block = extract_main_content(soup)
    if not content_block:
        print("❌ Aucun contenu trouvé sur cette page.")
        sys.exit(1)

    book = epub.EpubBook()
    book.set_identifier(url)
    book.set_title(title)
    book.add_author(author)
    book.set_language("fr")

    download_and_embed_images(content_block, url, book)

    # couverture
    if cover_url:
        try:
            c = fetch_url(cover_url)
            cover_bytes = c.content
            ext = "jpg"
            if "." in urlparse(cover_url).path:
                ext = urlparse(cover_url).path.split(".")[-1].split("?")[0] or "jpg"
            book.set_cover(f"cover.{ext}", cover_bytes)
        except Exception as e:
            print("⚠️  Échec de téléchargement de la couverture :", e)

    safe_pubdate = f"<p><em>{pubdate}</em></p>" if pubdate else ""
    chapter_html = f"<h1>{title}</h1>{safe_pubdate}{str(content_block)}"
    chapter = epub.EpubHtml(title=title, file_name="chapter.xhtml", lang="fr")
    chapter.content = chapter_html

    css = """
    body { font-family: serif; line-height: 1.5; margin: 1em; }
    img { max-width: 100%; height: auto; display: block; margin: 0.5em auto; }
    h1 { text-align: center; margin-bottom: 1em; }
    """
    style_item = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=css)
    book.add_item(style_item)
    book.add_item(chapter)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.toc = [epub.Link("chapter.xhtml", title, "chapter")]
    book.spine = ["nav", chapter]

    epub.write_epub(output_filename, book)
    print(f"\n✅ EPUB créé : {output_filename}\n")


def main():
    print("📚 Convertisseur Web → EPUB")
    print("----------------------------")
    url = input("➡️  Adresse de la page à convertir : ").strip()
    if not url:
        print("❌ URL obligatoire.")
        sys.exit(1)

    cover_url = input("🖼️  URL de l'image de couverture (laisser vide si aucune) : ").strip() or None
    output_filename = input("💾 Nom du fichier EPUB de sortie (ex: article.epub) : ").strip() or "article.epub"

    print("\n⏳ Téléchargement et création de l’EPUB...\n")
    build_epub(url, cover_url, output_filename)


if __name__ == "__main__":
    main()
