#!/usr/bin/env python3
"""Genera la web de Can Narcís a partir de src/plantilla.html.

Crea una pàgina per idioma (/, /es/, /en/, /fr/, /it/, /de/) amb el text ja
escrit dins l'HTML (perquè Google el llegeixi), etiquetes per a cercadors,
dades estructurades i sitemap.xml.

Ús:  python3 build.py      (necessita Python 3 i Playwright amb Chromium)
"""
import json, os, http.server, socketserver, threading, functools, html

SITE = "https://alexfont21.github.io/can-narcis/"   # canviar si es posa domini propi
LANGS = ["ca", "es", "en", "fr", "it", "de"]
ROOT = os.path.dirname(os.path.abspath(__file__))

META = {
 "ca": ("Can Narcís · Masia del 1688 per a grups a l'Empordà (fins a 12 persones)",
        "Casa rural sencera a Casavells, Baix Empordà: masia de pedra reformada, 5 habitacions, pati, garatge i wifi. A prop de Peratallada, la Costa Brava i Girona.",
        "ca_ES"),
 "es": ("Can Narcís · Masía de 1688 para grupos en el Empordà (hasta 12 personas)",
        "Casa rural entera en Casavells, Baix Empordà: masía de piedra reformada, 5 habitaciones, patio, garaje y wifi. Cerca de Peratallada, la Costa Brava y Girona.",
        "es_ES"),
 "en": ("Can Narcís · 1688 stone farmhouse for groups in the Empordà, Costa Brava (sleeps 12)",
        "Whole holiday house in Casavells, Baix Empordà: restored stone farmhouse with 5 bedrooms, courtyard, garage and wifi. Near Peratallada, the Costa Brava and Girona.",
        "en_GB"),
 "fr": ("Can Narcís · Mas de 1688 pour groupes dans l'Empordà, Costa Brava (jusqu'à 12 pers.)",
        "Maison entière à Casavells, Baix Empordà : mas en pierre rénové, 5 chambres, cour, garage et wifi. Près de Peratallada, de la Costa Brava et de Girona.",
        "fr_FR"),
 "it": ("Can Narcís · Casale del 1688 per gruppi nell'Empordà, Costa Brava (fino a 12 persone)",
        "Casa vacanze intera a Casavells, Baix Empordà: casale in pietra ristrutturato, 5 camere, cortile, garage e wifi. Vicino a Peratallada, Costa Brava e Girona.",
        "it_IT"),
 "de": ("Can Narcís · Landhaus von 1688 für Gruppen im Empordà, Costa Brava (bis 12 Personen)",
        "Ganzes Ferienhaus in Casavells, Baix Empordà: restauriertes Steinhaus mit 5 Schlafzimmern, Hof, Garage und WLAN. Nahe Peratallada, Costa Brava und Girona.",
        "de_DE"),
}

def url(l):
    return SITE + ("" if l == "ca" else l + "/")

def head(l):
    title, desc, loc = META[l]
    e = html.escape
    alt = "\n".join(f'<link rel="alternate" hreflang="{x}" href="{url(x)}">' for x in LANGS)
    ld = {
        "@context": "https://schema.org",
        "@type": "LodgingBusiness",
        "name": "Can Narcís",
        "description": desc,
        "url": url(l),
        "inLanguage": l,
        "image": [SITE + f"fotos/casa-{n:02d}.jpg" for n in (1, 21, 24, 4, 3, 15)],
        "address": {"@type": "PostalAddress", "addressLocality": "Casavells, Corçà",
                    "addressRegion": "Girona", "postalCode": "17121", "addressCountry": "ES"},
        "numberOfRooms": 5,
        "petsAllowed": True,
        "amenityFeature": [{"@type": "LocationFeatureSpecification", "name": n, "value": True} for n in
                           ["Wifi", "Heating", "Air conditioning", "Fireplace", "Free parking",
                            "Garage", "Barbecue", "Washing machine", "Bicycles", "Private courtyard"]],
        "sameAs": ["https://www.airbnb.es/rooms/40228287"],
    }
    return f'''<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url(l)}">
{alt}
<link rel="alternate" hreflang="x-default" href="{url('ca')}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Can Narcís">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url(l)}">
<meta property="og:image" content="{SITE}fotos/casa-01.jpg">
<meta property="og:locale" content="{loc}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'''

def build_raw():
    tpl = open(os.path.join(ROOT, "src", "plantilla.html"), encoding="utf-8").read()
    out = []
    for l in LANGS:
        base = "" if l == "ca" else "../"
        s = tpl.replace("<!--HEAD-->", head(l)).replace("{{LANG}}", l).replace("{{BASE}}", base)
        for x in LANGS:
            s = s.replace("{{L_%s}}" % x, (base + ("" if x == "ca" else x + "/")) or "./")
        assert "{{" not in s, l
        path = "index.html" if l == "ca" else f"{l}/index.html"
        os.makedirs(os.path.dirname(os.path.join(ROOT, path)) or ROOT, exist_ok=True)
        open(os.path.join(ROOT, path), "w", encoding="utf-8").write(s)
        out.append(path)
    return out

def prerender(paths):
    """Executa la pàgina en un navegador i guarda l'HTML ja amb tot el text."""
    from playwright.sync_api import sync_playwright
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    handler = functools.partial(Quiet, directory=ROOT)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for path in paths:
                pg = b.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(f"http://127.0.0.1:{port}/{path.replace('index.html', '')}")
                pg.wait_for_timeout(300)
                if errs:
                    raise SystemExit(f"{path}: {errs}")
                doc = "<!doctype html>\n" + pg.evaluate("document.documentElement.outerHTML")
                open(os.path.join(ROOT, path), "w", encoding="utf-8").write(doc)
                pg.close()
            b.close()
    finally:
        srv.shutdown()

def sitemap():
    rows = []
    for l in LANGS:
        alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{x}" href="{url(x)}"/>' for x in LANGS)
        rows.append(f"  <url>\n    <loc>{url(l)}</loc>{alts}\n  </url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(xml)

if __name__ == "__main__":
    paths = build_raw()
    prerender(paths)
    sitemap()
    print("Fet:", ", ".join(paths), "+ sitemap.xml")
