#!/usr/bin/env python3
"""Builds and signs the APK without the Android SDK or Gradle.

Needs: JDK (javac), android.jar (API 34), aapt2, dx.jar, Python 'cryptography'.
Usage: python3 tools/build_apk_local.py --android-jar PATH --aapt2 PATH --dx PATH --version N --out chyle-czola.apk
"""
import argparse, hashlib, os, pathlib, re, shutil, struct, subprocess, tempfile, zipfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"
PACKAGE = "pl.tytus42.chyleczola"


def run(cmd):
    print("$", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True)


# ---------- zip with 4-byte aligned stored entries (what zipalign does) ----------
def write_aligned(entries, out_path):
    """entries: list of (name, bytes, compress: bool)."""
    with open(out_path, "wb") as fh, zipfile.ZipFile(fh, "w") as z:
        for name, data, compress in entries:
            info = zipfile.ZipInfo(name, date_time=(2008, 1, 1, 0, 0, 0))
            info.create_system = 0
            info.external_attr = 0
            if compress:
                info.compress_type = zipfile.ZIP_DEFLATED
            else:
                info.compress_type = zipfile.ZIP_STORED
                offset = fh.tell() + 30 + len(name.encode())
                pad = (-offset) % 4
                if pad:
                    info.extra = b"\x00" * pad
            z.writestr(info, data)


# ---------- APK Signature Scheme v2 ----------
def lp(b):
    return struct.pack("<I", len(b)) + b


def find_eocd(data):
    i = data.rfind(b"PK\x05\x06")
    if i < 0:
        raise ValueError("no EOCD")
    return i


def chunk_digest(sections):
    chunks = []
    for sec in sections:
        for i in range(0, len(sec), 1 << 20):
            c = sec[i:i + (1 << 20)]
            chunks.append(hashlib.sha256(b"\xa5" + struct.pack("<I", len(c)) + c).digest())
    return hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks)) + b"".join(chunks)).digest()


def sign_v2(apk_bytes, key, cert_der):
    eocd = find_eocd(apk_bytes)
    cd_size, cd_off = struct.unpack("<II", apk_bytes[eocd + 12:eocd + 20])
    entries = apk_bytes[:cd_off]
    cd = apk_bytes[cd_off:cd_off + cd_size]
    eocd_bytes = apk_bytes[eocd:]

    alg = 0x0103  # RSASSA-PKCS1-v1_5 with SHA2-256
    digest = chunk_digest([entries, cd, eocd_bytes])
    signed_data = (lp(lp(struct.pack("<I", alg) + lp(digest)))
                   + lp(lp(cert_der))
                   + lp(b""))
    sig = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    pub = key.public_key().public_bytes(serialization.Encoding.DER,
                                        serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = lp(signed_data) + lp(lp(struct.pack("<I", alg) + lp(sig))) + lp(pub)
    value = lp(lp(signer))
    pair = struct.pack("<Q", 4 + len(value)) + struct.pack("<I", 0x7109871a) + value
    size = len(pair) + 8 + 16
    block = struct.pack("<Q", size) + pair + struct.pack("<Q", size) + b"APK Sig Block 42"

    new_eocd = bytearray(eocd_bytes)
    struct.pack_into("<I", new_eocd, 16, cd_off + len(block))
    return entries + block + cd + bytes(new_eocd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--android-jar", required=True)
    ap.add_argument("--aapt2", required=True)
    ap.add_argument("--dx", required=True)
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--out", default="chyle-czola.apk")
    a = ap.parse_args()

    work = pathlib.Path(tempfile.mkdtemp(prefix="apkbuild-"))
    src = APP / "src/main"

    # 1. Java -> .class -> classes.dex
    classes = work / "classes"
    classes.mkdir()
    java_files = sorted(str(p) for p in (src / "java").rglob("*.java"))
    run(["javac", "-nowarn", "-encoding", "UTF-8", "-source", "8", "-target", "8",
         "-bootclasspath", a.android_jar, "-classpath", a.android_jar, "-d", classes] + java_files)
    run(["java", "-jar", a.dx, "--dex", "--min-sdk-version=26", f"--output={work / 'classes.dex'}", classes])

    # 2. Resources, manifest, assets via aapt2
    manifest = (src / "AndroidManifest.xml").read_text(encoding="utf-8")
    manifest = manifest.replace("<manifest ", f'<manifest package="{PACKAGE}" ', 1)
    (work / "AndroidManifest.xml").write_text(manifest, encoding="utf-8")
    run([a.aapt2, "compile", "--dir", src / "res", "-o", work / "res.zip"])
    run([a.aapt2, "link", "-o", work / "base.apk", "-I", a.android_jar,
         "--manifest", work / "AndroidManifest.xml", "-A", src / "assets",
         "--min-sdk-version", "26", "--target-sdk-version", "34",
         "--version-code", str(a.version), "--version-name", f"1.0.{a.version}",
         work / "res.zip"])

    # 3. Repack: manifest first, resources.arsc stored and aligned, add dex
    entries = []
    with zipfile.ZipFile(work / "base.apk") as z:
        names = z.namelist()
        names.sort(key=lambda n: (n != "AndroidManifest.xml", n))
        for n in names:
            stored = n == "resources.arsc" or n.endswith(".png")
            entries.append((n, z.read(n), not stored))
    entries.insert(1, ("classes.dex", (work / "classes.dex").read_bytes(), True))
    write_aligned(entries, work / "unsigned.apk")

    # 4. Sign (v2) with the project key
    key, cert, _ = pkcs12.load_key_and_certificates((APP / "chyle.keystore").read_bytes(), b"chyleczola")
    signed = sign_v2((work / "unsigned.apk").read_bytes(), key,
                     cert.public_bytes(serialization.Encoding.DER))
    pathlib.Path(a.out).write_bytes(signed)
    print("APK:", a.out, len(signed), "bytes")
    shutil.rmtree(work)


if __name__ == "__main__":
    main()
