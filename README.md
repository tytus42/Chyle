# Chylę czoła

Imprezowa gra w zgadywanie haseł z czoła, w stylu neo-brutalizmu. Aplikacja na Androida (8.0+).

## Instalacja
Wejdź w zakładkę **Releases** → **latest** i pobierz `chyle-czola.apk` na telefonie. Przy instalacji Android poprosi o zgodę na instalowanie aplikacji z przeglądarki.

## Jak to jest zbudowane
- `web/chyle-czola.html` – cała gra (HTML, CSS, JS w jednym pliku).
- `tools/sync_web.py` – kopiuje grę do `app/src/main/assets/index.html` i podmienia czcionki Google na wbudowane, żeby apka działała bez internetu.
- `app/` – lekka aplikacja Android (WebView na pełnym ekranie, blokada obrotu w trakcie rundy, ekran nie gaśnie, przycisk Wstecz wraca do menu).
- Każdy push do `main` buduje APK w GitHub Actions i publikuje go jako wydanie `latest`.

Po zmianie gry: edytuj `web/chyle-czola.html`, uruchom `python3 tools/sync_web.py` i wypchnij zmiany.

Czcionki: Archivo Black, Archivo, JetBrains Mono (SIL Open Font License 1.1).

## Budowanie bez Android SDK
`tools/build_apk_local.py` składa i podpisuje APK samym JDK, aapt2, dx i Pythonem (podpis APK Signature Scheme v2). Przydaje się, gdy nie ma dostępu do Android SDK.
