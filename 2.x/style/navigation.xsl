<?xml version="1.0"?><!-- -*- Mode: xml; tab-width: 2 -*- -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:str="http://exslt.org/strings"
                xmlns:func="http://exslt.org/functions"
                extension-element-prefixes="str func"
                version="1.0">

<xsl:param name="lang" select="'C'"/>
<xsl:param name="basename" select="''"/>
<xsl:param name="root" select="''"/>
<xsl:param name="prefix" select="''"/>
<xsl:param name="http_root" select="''"/>
<xsl:param name="http_prefix" select="''"/>

<xsl:template match="bar" mode="header">
	<xsl:for-each select="item">
		<xsl:if test="position() != 1">
			<xsl:text> &#183; </xsl:text>
		</xsl:if>
		<xsl:apply-templates select="." mode="header"/>
	</xsl:for-each>
</xsl:template>

<xsl:template match="bar" mode="sidebar">
	<xsl:param name="expand-all" select="false()"/>
	<xsl:param name="target"
		select="concat($http_root, $http_prefix, $basename)"/>
	<p class="section">
		<xsl:choose>
			<xsl:when test="title[@xml:lang = $lang]">
				<xsl:copy-of select="title[@xml:lang = $lang][1]/node()"/>
			</xsl:when>
			<xsl:when test="title[not(@xml:lang)]">
				<xsl:copy-of select="title[not(@xml:lang)][1]/node()"/>
			</xsl:when>
		</xsl:choose>
	</p>
	<ul>
		<xsl:apply-templates select="item" mode="sidebar">
			<xsl:with-param name="expand-all" select="$expand-all"/>
			<xsl:with-param name="target" select="$target"/>
		</xsl:apply-templates>
	</ul>
</xsl:template>

<xsl:template match="item" mode="sidebar">
	<xsl:param name="expand-all" select="false()"/>
	<xsl:param name="target"
		select="concat($http_root, $http_prefix, $basename)"/>
	<xsl:variable name="title">
		<xsl:choose>
			<xsl:when test="title[@xml:lang = $lang]">
				<xsl:copy-of select="title[@xml:lang = $lang][1]/node()"/>
			</xsl:when>
			<xsl:when test="title[not(@xml:lang)]">
				<xsl:copy-of select="title[not(@xml:lang)][1]/node()"/>
			</xsl:when>
		</xsl:choose>
	</xsl:variable>
	<li>
		<xsl:choose>
			<xsl:when test="not(func:is-target(., $target))">
				<a href="{@href}"><xsl:copy-of select="$title"/></a>
			</xsl:when>
			<xsl:otherwise>
				<xsl:copy-of select="$title"/>
			</xsl:otherwise>
		</xsl:choose>
		<xsl:if test="item and ($expand-all or func:contains-target())">
			<ul><xsl:apply-templates select="item" mode="sidebar">
				<xsl:with-param name="expand-all" select="$expand-all"/>
				<xsl:with-param name="target" select="$target"/>
			</xsl:apply-templates></ul>
		</xsl:if>
	</li>
</xsl:template>

<xsl:template match="item" mode="header">
	<xsl:variable name="title">
		<xsl:choose>
			<xsl:when test="title[@xml:lang = $lang]">
				<xsl:copy-of select="title[@xml:lang = $lang][1]/node()"/>
			</xsl:when>
			<xsl:when test="title[not(@xml:lang)]">
				<xsl:copy-of select="title[not(@xml:lang)][1]/node()"/>
			</xsl:when>
		</xsl:choose>
	</xsl:variable>
	<xsl:choose>
		<xsl:when test="func:is-target()">
			<b><xsl:copy-of select="$title"/></b>
		</xsl:when>
		<xsl:when
				test="starts-with(concat($http_root, $http_prefix, $basename), @href)">
			<a href="{@href}"><b><xsl:copy-of select="$title"/></b></a>
		</xsl:when>
		<xsl:otherwise>
			<a href="{@href}"><xsl:copy-of select="$title"/></a>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>

<func:function name="func:is-target">
	<xsl:param name="node" select="."/>
	<xsl:param name="target"
		select="concat($http_root, $http_prefix, $basename)"/>
	<xsl:variable name="href" select="$node/@href"/>
	<xsl:choose>
		<xsl:when test="$href = $target">
			<func:result select="true()"/>
		</xsl:when>
		<xsl:when test="starts-with($target, $href)
				and (concat($href, 'index') = $target)">
			<func:result select="true()"/>
		</xsl:when>
		<xsl:otherwise>
			<func:result select="false()"/>
		</xsl:otherwise>
	</xsl:choose>
</func:function>

<func:function name="func:contains-target">
	<xsl:param name="node" select="."/>
	<xsl:param name="target"
		select="concat($http_root, $http_prefix, $basename)"/>
	<func:result select="
			func:is-target($node, $target) or
			$node/item[func:contains-target(., $target)]
		"/>
</func:function>

</xsl:stylesheet>

