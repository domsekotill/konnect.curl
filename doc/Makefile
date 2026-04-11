SPHINXBUILD = sphinx-build
SPHINXOPTS = -j auto
SPHINXAPIDOC = sphinx-apidoc
SPHINXAPIDOCOPTS = --separate
BUILDDIR = build

# Alternatives: html dirhtml singlehtml
HTML_BUILDER = html

# Values above this line may be modified from cmdline
# ======

BUILD_SRC = Makefile conf.py
SPHINX_SRC = $(BUILD_SRC) index.md konnect.curl.rst
#SPHINX_SRC += **additional .md files**
APIDOC_SRC := $(BUILD_SRC)
APIDOC_SRC += $(wildcard ../konnect/curl/*.py)
APIDOC_SRC += $(wildcard templates/apidoc/*.rst_t)

BUILDOUT = $(@D)


.PHONY: default all
default:

.PHONY all default: html
html: BUILDER=$(HTML_BUILDER)
html: doctest $(BUILDDIR)/html/index.html

.PHONY all: man
man: BUILDER=man
man: doctest $(BUILDDIR)/man/konnectkonnectcurl.1

.PHONY all: text
text: BUILDER=text
text: doctest $(BUILDDIR)/text/index.txt

.PHONY: doctest
doctest: BUILDER=doctest
doctest: $(BUILDDIR)/doctest/output.txt $(APIDOC_SRC)

.PHONY: clean
clean:
	-rm -rf $(BUILDDIR)
	-rm konnect.*


konnect.curl.rst: $(BUILD_SRC) $(APIDOC_SRC)
	$(SPHINXAPIDOC) $(SPHINXAPIDOCOPTS) --implicit-namespaces -MTft templates/apidoc -o . ../konnect
	@rm konnect.rst
	@touch $@

$(BUILDDIR)/%: $(BUILD_SRC) $(SPHINX_SRC) | $(BUILDDIR)
	$(SPHINXBUILD) -ab $(BUILDER) $(SPHINXOPTS) . $(BUILDOUT)

$(BUILDDIR):
	mkdir -p $@
