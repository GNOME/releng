<?xml version='1.0'?><!-- -*- Mode: xml; tab-width: 2 -*- -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:func="http://exslt.org/functions"
                xmlns:exsl="http://exslt.org/common"
                xmlns:yelp="http://www.gnome.org/"
                extension-element-prefixes="func exsl"
                version='1.0'>

<xsl:include href="yelp-customization.xsl"/>
<xsl:include href="navigation.xsl"/>
<xsl:include href="l10n.xsl"/>

<xsl:param name="lang" select="'C'"/>

<xsl:param name="yelp_max_chunk_depth" select="2" />
<xsl:param name="yelp_generate_navbar" select="true()"/>
<xsl:param name="yelp_chunk_method" select="'exslt'"/>

<xsl:variable name="navigation">
	<navigation><bar id="docbook">
		<title xml:lang="{$lang}">
			<xsl:call-template name="gettext">
				<xsl:with-param name="key" select="'Sections'"/>
			</xsl:call-template>
		</title>
		<item href="index.html">
			<title xml:lang="{$lang}">
				<xsl:value-of select="yelp:get-title-text(/article)"/>
			</title>
		</item>
		<xsl:apply-templates
				select="yelp:get-divisions(/*)" mode="navigation-mode">
			<xsl:with-param name="depth" select="1"/>
		</xsl:apply-templates>
	</bar></navigation>
</xsl:variable>

<xsl:output encoding="ISO-8859-1" />

<!-- ======================================================================= -->
<!-- Here we override Yelp's chunking template. -->

<xsl:template name="yelp.chunk">
	<xsl:param name="node" select="."/>
	<xsl:param name="id" select="$node/@id"/>
	<xsl:param name="content">
		<xsl:apply-templates select="$node"/>
	</xsl:param>

	<xsl:variable name="filename">
		<xsl:choose>
			<xsl:when test="$id = 'title-page'">
				<xsl:text>titlepage.html</xsl:text>
			</xsl:when>
			<xsl:when test="$id = 'toc'">
				<xsl:text>index.html</xsl:text>
			</xsl:when>
			<xsl:otherwise>
				<xsl:value-of select="concat($id, '.html')"/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:variable>

	<exsl:document href="{$filename}">
		<xsl:apply-templates select="document('template.xml')/*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
	</exsl:document>
</xsl:template>

<!-- ======================================================================= -->
<!-- Here we process template.xml -->

<xsl:template match="* | @*" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:copy>
		<xsl:apply-templates select="node() | @*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
	</xsl:copy>
</xsl:template>

<xsl:template match="title" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:copy>
		<xsl:apply-templates select="@*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
		<xsl:value-of select="yelp:get-title-text($node)"/>
	</xsl:copy>
</xsl:template>

<xsl:template match="div[@id = 'body']" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:copy>
		<xsl:apply-templates select="@*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
		<xsl:copy-of select="exsl:node-set($content)/hr[1]/following-sibling::*"/>
	</xsl:copy>
</xsl:template>

<xsl:template match="div[@id = 'hdrNav']" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:variable name="navfile" select="document('navigation.xml')"/>
	<xsl:variable name="navid" select="'top-users'"/>
	<xsl:copy>
		<xsl:apply-templates select="@*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
		<xsl:apply-templates select="$navfile//bar[@id = $navid]" mode="header"/>
	</xsl:copy>
</xsl:template>

<xsl:template match="div[@id = 'sidebar']" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:copy>
		<xsl:apply-templates select="@*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
		<xsl:apply-templates select="exsl:node-set($navigation)//bar" mode="sidebar">
			<xsl:with-param name="expand-all" select="true()"/>
			<xsl:with-param name="target">
				<xsl:choose>
					<xsl:when test="$id = 'title-page'">
						<xsl:text>titlepage.html</xsl:text>
					</xsl:when>
					<xsl:when test="$id = 'toc'">
						<xsl:text>index.html</xsl:text>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="concat($id, '.html')"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:with-param>
		</xsl:apply-templates>
	</xsl:copy>
</xsl:template>

<xsl:template match="div[@id = 'copyright']" mode="template-mode">
	<xsl:param name="node"/>
	<xsl:param name="id"/>
	<xsl:param name="content"/>
	<xsl:copy>
		<xsl:apply-templates select="@*" mode="template-mode">
			<xsl:with-param name="node" select="$node"/>
			<xsl:with-param name="id" select="$id"/>
			<xsl:with-param name="content" select="$content"/>
		</xsl:apply-templates>
		<xsl:apply-templates
			select="$node/ancestor::book/bookinfo//copyright       |
              $node/ancestor::article/articleinfo//copyright "
			mode="copyright-footer-mode"/>
	</xsl:copy>
</xsl:template>

<xsl:template match="copyright" mode="copyright-footer-mode">
	<xsl:call-template name="gettext">
	  <xsl:with-param name="key" select="'Copyright'"/>
	</xsl:call-template>
	<xsl:call-template name="gentext.space"/>
	<xsl:call-template name="dingbat">
		<xsl:with-param name="dingbat">copyright</xsl:with-param>
	</xsl:call-template>
	<xsl:call-template name="gentext.space"/>
	<xsl:call-template name="copyright.years">
		<xsl:with-param name="years" select="year"/>
		<xsl:with-param name="print.ranges" select="$make.year.ranges"/>
		<xsl:with-param name="single.year.ranges" select="$make.single.year.ranges"/>
	</xsl:call-template>
	<xsl:call-template name="gentext.space"/>
	<xsl:apply-templates select="holder" mode="titlepage.mode"/>
 	<xsl:if test="position() != last()"><br/></xsl:if>
</xsl:template>

<!-- ======================================================================= -->
<!-- Here we construct navigation XML for the DocBook. -->

<xsl:template match="*[yelp:is-division(.)]" mode="navigation-mode">
	<xsl:param name="depth" select="0"/>
	<item href="{concat(@id, '.html')}">
		<xsl:choose>
			<xsl:when test="($lang != '') and ($lang != 'C')">
				<title xml:lang="{$lang}">
					<xsl:value-of select="yelp:get-title-text(.)"/>
				</title>
			</xsl:when>
			<xsl:otherwise>
				<title xml:lang="{$lang}">
					<xsl:value-of select="yelp:get-title-text(.)"/>
				</title>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:if test="$depth &lt; $yelp_max_chunk_depth">
			<xsl:apply-templates
					select="yelp:get-divisions(.)" mode="navigation-mode">
				<xsl:with-param name="depth" select="$depth + 1"/>
			</xsl:apply-templates>
		</xsl:if>
	</item>
</xsl:template>

<!-- == == == -->

<xsl:template name="yelp.root">
	<xsl:variable name="next" select="yelp:get-next(.)"/>

	<xsl:call-template name="yelp.chunk">
		<xsl:with-param name="id" select="'toc'"/>
		<xsl:with-param name="node" select="."/>
		<xsl:with-param name="content">
			<xsl:call-template name="yelp.navbar.top">
				<xsl:with-param name="node" select="."/>
				<xsl:with-param name="prev" select="false()"/>
				<xsl:with-param name="next" select="$next"/>
			</xsl:call-template>
			<xsl:call-template name="yelp.title"/>
			<xsl:apply-templates select="yelp:get-content(.)"/>
			<div class="abstract">
				<xsl:apply-templates select="/article/articleinfo/abstract"/>
			</div>
			<xsl:call-template name="yelp.navbar.bottom">
				<xsl:with-param name="node" select="."/>
				<xsl:with-param name="prev" select="false()"/>
				<xsl:with-param name="next" select="$next"/>
				<xsl:with-param name="up" select="false()"/>
			</xsl:call-template>
		</xsl:with-param>
	</xsl:call-template>

	<xsl:for-each select="yelp:get-divisions(.)">
		<xsl:call-template name="yelp.component.chunk">
			<xsl:with-param name="depth" select="1"/>
		</xsl:call-template>
	</xsl:for-each>
</xsl:template>

<xsl:template name="yelp.navbar">
	<xsl:param name="node" select="."/>
	<xsl:param name="prev" select="yelp:get-prev($node)"/>
	<xsl:param name="next" select="yelp:get-next($node)"/>
	<xsl:param name="up" select="false()"/>
	<xsl:param name="use.title" select="false()"/>

	<xsl:if test="$yelp_generate_navbar">
	<table width="100%"><tr>
		<xsl:call-template name="yelp.navbar.cell">
			<xsl:with-param name="target" select="$prev"/>
			<xsl:with-param name="use.title" select="$use.title"/>
			<xsl:with-param name="position" select="'left'"/>
		</xsl:call-template>
		<xsl:if test="$up">
			<td align="center" valign="top" width="20%"><a accesskey="u">
				<xsl:attribute name="href">
					<xsl:call-template name="yelp.toc.ref"/>
				</xsl:attribute>
				<xsl:value-of select="yelp:get-title-text(/article/articleinfo/abstract)"/>
			</a></td>
		</xsl:if>
		<xsl:call-template name="yelp.navbar.cell">
			<xsl:with-param name="target" select="$next"/>
			<xsl:with-param name="use.title" select="$use.title"/>
			<xsl:with-param name="position" select="'right'"/>
		</xsl:call-template>
	</tr></table>
	</xsl:if>
</xsl:template>

<xsl:template name="yelp.navbar.cell">
	<xsl:param name="target" select="."/>
	<xsl:param name="show.title" select="false()"/>
	<xsl:param name="position" select="'left'"/>
	<xsl:param name="use.title" select="false()"/>

	<td width="40%" valign="top">
		<xsl:attribute name="align">
			<xsl:value-of select="$position"/>
		</xsl:attribute>
		<xsl:if test="$target">
		<a>
			<xsl:attribute name="accesskey">
				<xsl:choose>
					<xsl:when test="$position = 'left'"><xsl:text>p</xsl:text></xsl:when>
					<xsl:when test="$position = 'right'"><xsl:text>n</xsl:text></xsl:when>
				</xsl:choose>
			</xsl:attribute>
			<xsl:attribute name="href">
				<xsl:choose>
					<xsl:when test="$target = 'title-page'">
						<xsl:call-template name="yelp.titlepage.ref"/>
					</xsl:when>
					<xsl:when test="$target = 'toc'">
						<xsl:call-template name="yelp.toc.ref"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:call-template name="href.target">
							<xsl:with-param name="object" select="$target"/>
						</xsl:call-template>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<xsl:choose>
				<xsl:when test="$position = 'left'">
					<xsl:call-template name="gentext">
						<xsl:with-param name="key" select="'Previous'"/>
					</xsl:call-template>
				</xsl:when>
				<xsl:when test="$position = 'right'">
					<xsl:call-template name="gentext">
						<xsl:with-param name="key" select="'Next'"/>
					</xsl:call-template>
				</xsl:when>
			</xsl:choose>
		</a>
		<xsl:if test="$use.title">
			<br/>
			<xsl:choose>
				<xsl:when test="$target = 'title-page'">
					<xsl:call-template name="gentext.template">
						<xsl:with-param name="context" select="'title'"/>
						<xsl:with-param name="name" select="'bookinfo'"/>
					</xsl:call-template>
				</xsl:when>
				<xsl:when test="$target = 'toc'">
					<xsl:call-template name="gentext">
						<xsl:with-param name="key" select="'Contents'"/>
					</xsl:call-template>
				</xsl:when>
				<xsl:otherwise>
					<xsl:value-of select="yelp:get-title-text($target)"/>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:if>
		</xsl:if>
	</td>
</xsl:template>

</xsl:stylesheet>
