#!/usr/bin/env python3
"""Builds app/src/main/assets/index.html from web/chyle-czola.html.
Swaps the Google Fonts link for fonts bundled in the app, so the game works offline."""
import re, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
src = (root / "web" / "chyle-czola.html").read_text(encoding="utf-8")
LATIN = "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD"
EXT = "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF"
faces = [("Archivo Black", "archivo-black", [400]), ("Archivo", "archivo", [400, 500, 700, 800]), ("JetBrains Mono", "jetbrains-mono", [700, 800])]
css = []
for fam, slug, weights in faces:
    for w in weights:
        for sub, rng in (("latin-ext", EXT), ("latin", LATIN)):
            css.append(f"@font-face{{font-family:'{fam}';font-style:normal;font-weight:{w};font-display:swap;"
                       f"src:url(fonts/{slug}-{sub}-{w}-normal.woff2) format('woff2');unicode-range:{rng}}}")
body = re.sub(r'<link rel="preconnect"[^>]*>\n?', "", src)
body = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^"]*">\n?', "", body)
body = re.sub(r'<meta charset="utf-8">\n?|<meta name="viewport"[^>]*>\n?', "", body)
# The app passes the camera-cutout size as --ai-* variables, because WebView does not always fill env(safe-area-inset-*).
body = re.sub(r"env\(safe-area-inset-(left|right|top|bottom),\s*0px\)", r"max(env(safe-area-inset-\1,0px),var(--ai-\1,0px))", body)
out = ("<!doctype html><html lang=\"pl\"><head><meta charset=\"utf-8\">"
       "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no\">"
       "<style>" + "\n".join(css) + "\nhtml{height:100%}"
       "html,body{margin:0;-webkit-tap-highlight-color:transparent}img{max-width:100%}</style>"
       "</head><body>\n" + body + "\n</body></html>\n")
(root / "app/src/main/assets/index.html").write_text(out, encoding="utf-8")
print("index.html:", len(out), "bytes")
