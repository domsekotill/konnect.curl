SPHINXBUILD = sphinx-build
SPHINXOPTS = -j auto
SPHINXAPIDOC = sphinx-apidoc
SPHINXAPIDOCOPTS = --separate
BUILDDIR = build

# Alternatives: html dirhtml singlehtml
HTML_BUILDER = html

# Values above this line may be modified from cmdline
# ======

PKG_NAMESPACE = konnect
PKG_NAME = curl

BUILD_SRC = Makefile conf.py
SPHINX_SRC = $(BUILD_SRC) index.md $(PKG_NAMESPACE).$(PKG_NAME).rst
#SPHINX_SRC += **additional .md files**
APIDOC_SRC := $(BUILD_SRC)
APIDOC_SRC += $(wildcard ../$(PKG_NAMESPACE)/$(PKG_NAME)/*.py)
APIDOC_SRC += $(wildcard templates/apidoc/*.rst_t)

BUILDOUT = $(@D)


.PHONY: default all
default:

.PHONY all default: html
html: BUILDER=$(HTML_BUILDER)
html: doctest $(BUILDDIR)/html/index.html

.PHONY all: man
man: BUILDER=man
man: doctest $(BUILDDIR)/man/$(PKG_NAMESPACE)$(PKG_NAMESPACE)$(PKG_NAME).1

.PHONY all: text
text: BUILDER=text
text: doctest $(BUILDDIR)/text/index.txt

.PHONY: doctest
doctest: BUILDER=doctest
doctest: $(BUILDDIR)/doctest/output.txt $(APIDOC_SRC)

.PHONY: clean
clean:
	-rm -rf $(BUILDDIR)
	-rm $(PKG_NAMESPACE).*


$(PKG_NAMESPACE).$(PKG_NAME).rst: $(BUILD_SRC) $(APIDOC_SRC)
	$(SPHINXAPIDOC) $(SPHINXAPIDOCOPTS) --implicit-namespaces -MTft templates/apidoc -o . ../$(PKG_NAMESPACE)
	@rm $(PKG_NAMESPACE).rst
	@touch $@

$(BUILDDIR)/%: $(BUILD_SRC) $(SPHINX_SRC) | $(BUILDDIR)
	$(SPHINXBUILD) -ab $(BUILDER) $(SPHINXOPTS) . $(BUILDOUT)

$(BUILDDIR):
	mkdir -p $@
