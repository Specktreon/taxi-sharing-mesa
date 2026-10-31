"""Build report.pdf: report/report.md -> report/report.html -> report.pdf.

Run from the project folder: python report/build.py
Uses the `markdown` package and Chrome headless; prints the page count.
"""

import re
import subprocess
from pathlib import Path

import markdown

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SRC = Path("report/report.md")
HTML = Path("report/report.html")
PDF = Path("report.pdf")

CSS = """
@page { size: A4; margin: 2cm; }
html { font-size: 10.5pt; }
body { font-family: "Times New Roman", Georgia, serif; line-height: 1.32;
       color: #111; margin: 0; }
.titleblock { text-align: center; margin-bottom: 0.6em; }
.titleblock h1 { font-size: 17pt; margin: 0 0 0.25em 0; }
.titleblock p { margin: 0.1em 0; }
.authors { font-size: 12pt; }
.meta { font-size: 9.5pt; color: #333; }
h2 { font-size: 12.5pt; margin: 0.9em 0 0.3em 0; break-after: avoid; }
p { margin: 0.35em 0; text-align: justify; hyphens: auto; }
ul { margin: 0.3em 0; padding-left: 1.3em; }
li { margin: 0.15em 0; text-align: justify; }
table { border-collapse: collapse; width: 100%; font-size: 7.8pt; margin: 0.3em 0 0.6em 0;
        break-inside: avoid; }
/* numeric tables only: long text cells elsewhere must wrap, or Chrome shrinks
   every page to fit the widest table */
.num td { white-space: nowrap; }
th, td { border-bottom: 0.5pt solid #bbb; padding: 1.5pt 3pt; text-align: left;
         vertical-align: top; }
th { border-bottom: 0.9pt solid #333; font-weight: bold; }
figure { margin: 0.5em 0 0.7em 0; text-align: center; break-inside: avoid; }
.keep { break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 9pt; color: #222; margin-top: 0.2em; text-align: center; }
code { font-family: Consolas, monospace; font-size: 9pt; }
"""


def build():
    body = markdown.markdown(SRC.read_text(encoding="utf-8"),
                             extensions=["tables", "md_in_html"])
    HTML.write_text(
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Taxi sharing in the city</title>"
        f"<style>{CSS}</style></head><body>{body}</body></html>",
        encoding="utf-8")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={PDF.resolve()}", str(HTML.resolve())],
                   check=True, capture_output=True)
    pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", PDF.read_bytes()))
    print(f"{PDF}: {pages} pages")
    return pages


if __name__ == "__main__":
    build()
