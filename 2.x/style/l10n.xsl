<?xml version="1.0"?><!-- -*- Mode: xml; tab-width: 2 -*- -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:str="http://exslt.org/strings"
                xmlns:exsl="http://exslt.org/common"
                xmlns:func="http://exslt.org/functions"
                extension-element-prefixes="str exsl"
                version="1.0">

<xsl:param name="lang"/>
<xsl:variable name="l10n" select="document('l10n.xml')/l10n"/>

<xsl:template name="gettext">
	<xsl:param name="key"/>
	<xsl:param name="lang" select="$lang"/>
	<xsl:choose>
		<xsl:when test="$l10n/key[@name = $key][@xml:lang = $lang]">
			<xsl:value-of select="$l10n/key[@name = $key][@xml:lang = $lang][1]"/>
		</xsl:when>
		<xsl:when test="$l10n/key[@name = $key][not(@xml:lang)]">
			<xsl:value-of select="$l10n/key[@name = $key][not(@xml:lang)][1]"/>
		</xsl:when>
		<xsl:otherwise>
			<xsl:message>
				<xsl:text>No entry found for key '</xsl:text>
				<xsl:value-of select="$key"/>
				<xsl:text>'</xsl:text>
			</xsl:message>
			<xsl:value-of select="$key"/>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>

<xsl:template name="gentext">
	<xsl:param name="key"/>
	<xsl:call-template name="gettext">
		<xsl:with-param name="key">
			<xsl:choose>
				<xsl:when test="$key = 'abstract'">
					<xsl:text>Abstract</xsl:text>
				</xsl:when>
				<xsl:when test="$key = 'legalnotice'">
					<xsl:text>Legal Notice</xsl:text>
				</xsl:when>
				<xsl:when test="$key = 'TableofContents'">
					<xsl:text>Table of Contents</xsl:text>
				</xsl:when>
				<xsl:otherwise><xsl:value-of select="$key"/></xsl:otherwise>
			</xsl:choose>
		</xsl:with-param>
		<xsl:with-param name="lang" select="$lang"/>
	</xsl:call-template>
</xsl:template>

<xsl:template name="sprintf">
	<xsl:param name="format"/>
	<xsl:param name="string"/>
	<xsl:choose>
		<xsl:when test="not(contains($format, '%s'))">
			<xsl:value-of select="$format"/>
		</xsl:when>
		<xsl:otherwise>
			<xsl:value-of select="substring-before($format, '%s')"/>
			<xsl:value-of select="$string"/>
			<xsl:value-of select="substring-after($format, '%s')"/>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>

</xsl:stylesheet>
