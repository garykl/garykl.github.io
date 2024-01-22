#!/usr/bin/bash

# there is no manually written .html
rm *.html
rm */*.html

# python 3.12 is needed, due to generic type syntax
python3.12 scripts/main.py

# categories and posts are rendered
asciidoctor -a stylesheet=style.css -a stylesdir=$(pwd) -a docinfodir=$(pwd)/docinfo -a docinfo=private-footer,private-header -r asciidoctor-diagram posts/*.adoc
asciidoctor -a stylesheet=style.css -a stylesdir=$(pwd) -a docinfodir=$(pwd)/docinfo -a docinfo=private-footer,private-header categories/*.adoc *.adoc
