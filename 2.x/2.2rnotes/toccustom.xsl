<?xml version='1.0'?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                version='1.0'>

<xsl:import href="http://docbook.sourceforge.net/release/xsl/current/html/chunktoc.xsl" />

<xsl:template name="user.header.content">
  <IMG>
    <xsl:attribute name="src">../figures/smallfoot.png</xsl:attribute>
  </IMG>
</xsl:template>
<!-- specify toc chunking -->
<xsl:param name="chunk.toc">rntoc.xml</xsl:param>

<!-- specify stylesheet -->
<xsl:param name="html.stylesheet">release.css</xsl:param>

<!-- only sect1's in TOC -->
<xsl:param name="toc.section.depth">2</xsl:param>

<!-- lose the rules in headers and footers -->
<xsl:param name="header.rule">0</xsl:param>
<xsl:param name="footer.rule">0</xsl:param>

</xsl:stylesheet>