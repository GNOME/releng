#!/usr/bin/perl
# Jeff's Totally Smeggy RelEng HTMLiser - 100% Smeg!
use Date::Format;

@linecolour = '#eeeeee', '#ffffff';
$gendate = time2str("%Y/%m/%d %T", time());

print qq{
<!--#set var="last_modified" value="\$Date$gendate \$" -->
};

print qq {
<table cellspacing="0" cellpadding="4" width="100%">
};
while (<STDIN>) {
	chomp;
	if ($_ eq "" || $_ =~ /^#/) {
		# ignore comments or blanks
		next;
	} elsif ($_ =~ s/<section title="(.*)">/$1/) {
		# format section titles
		print qq{
	<tr>
		<td colspan="4"><h3>$_</h3></td>
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
		# format end-of-sections
		print qq{
	<tr>
		<td colspan="4">&nbsp;</td>
	</tr>
};
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
		$package = "<a href=\"http://cvs.gnome.org/lxr/source/@module[0]/\">@module[0]</a>";
	} elsif (@module[1] eq "-" || @module[1] eq "") {
		$package = "@module[0]";
	} else {
		$package = "<a href=\"http://cvs.gnome.org/lxr/source/@module[1]/\">@module[0]</a> [@module[1]]";
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

print "\n</table>";
