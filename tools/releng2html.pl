#!/usr/bin/perl
# Jeff's Totally Smeggy RelEng HTMLiser - 100% Smeg!

@linecolour = '#eeeeee', '#ffffff';

print qq {<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
	<title>Modules</title>
</head>
<body bgcolor="#ffffff">
<table cellspacing="0" cellpadding="4" width="100%">
};
while (<STDIN>) {
	chomp;
	if ($_ eq "" || $_ =~ /^#/) {
		# ignore comments or blanks
		next;
	} elsif ($_ =~ /^<section/) {
		# grab title, and cvsbase if it's there
		$title = $_;
		$title =~ s/<section.*title="([^"]*)".*>/$1/;
		if ($_ =~ /cvsbase=".*"/) {
			$cvsbase = $_;
			$cvsbase =~ s/<section.*cvsbase="([^"]*)".*>/$1/;
		}
		# format section titles
		print qq{
	<tr>
		<td colspan="4"><h3>$title</h3></td>
	</tr>
	<tr bgcolor="#cccccc">
		<th align="left">package</th>
		<th align="left">version</th>
		<th align="left">status</th>
		<th align="left">contacts</th>
	</tr>
};
		next;
	} elsif ($_ eq "</section>") {
		$cvsbase = "";
		$count = 0;
		next;
	}
	
	# tab delimited
	@module = split(/\t+/, $_);

	# colour of line
	$count++;
	$bg = $linecolour[$count % 2];
	
	# make the cvs/module stuff pretty and understandable
	if (@module[1] eq "=") {
		$package = "<a href=\"http://cvs.gnome.org/lxr/source/$cvsbase/@module[0]/\">@module[0]</a>";
	} elsif (@module[1] eq "-" || @module[1] eq "") {
		$package = "@module[0]";
	} else {
		$package = "<a href=\"http://cvs.gnome.org/lxr/source/$cvsbase/@module[1]/\">@module[0]</a> [@module[1]]";
	}

	if (@module[3] =~ /\*.*/) {
		$bg = "#ffdddd";
	}

	# make contacts clicky
	@contacts = split(/\,/, @module[4]);
	foreach $contact (@contacts) {
		$contact =~ s/@/ AT /;
		$contact =~ s#(.*) <(.*)>#<a href="mailto:$2">$1</a>#;
	}
	$contacts = join(",", @contacts);
	
	# clag out a header
	print qq{
	<tr bgcolor="$bg" valign="top">
		<td nowrap>$package</td>
		<td>@module[2]</td>
		<td>@module[3]</td>
		<td>$contacts</td>
	</tr>};
}

print qq{</table>
</body>
</html>};
