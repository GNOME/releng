#!/usr/bin/perl

# Jeff's Totally Smeggy RelEng HTMLiser - 100% Smeg!

@linecolour = '#eeeeee', '#ffffff';

while (<STDIN>) {
	chomp;
	if ($_ eq "" || $_ =~ /^#/) {
		# ignore comments or blanks
		next;
	} elsif ($_ =~ s/<section title="(.*)">/$1/) {
		# format section titles
		print qq{
<h3>$_</h3>
<table cellspacing="0" cellpadding="4" width="100%">
	<tr bgcolor="#cccccc">
		<th>component</th>
		<th>version</th>
		<th>status</th>
		<th>contacts</th>
	</tr>
};
		next;
	} elsif ($_ eq "</section>") {
		# format end-of-sections
		print qq{
</table>
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
		$cvs = "<a href=\"http://cvs.gnome.org/lxr/source/@module[0]/\">@module[0]</a>";
	} elsif (@module[1] eq "-" || @module[1] eq "") {
		$cvs = "@module[0]";
	} else {
		$cvs = "<a href=\"http://cvs.gnome.org/lxr/source/@module[1]/\">@module[0]</a> [@module[1]]";
	}

	# make contacts clicky
	@contacts = split(/\,/, @module[4]);
	foreach $contact (@contacts) {
		$contact =~ s#(.*) <(.*)>#<a href="mailto:$2">$1</a>#;
	}
	$contacts = join(",", @contacts);
	
	# clag out a header
	print qq{
	<tr bgcolor="$bg" valign="top">
		<td>$cvs</td>
		<td>@module[2]</td>
		<td>@module[3]</td>
		<td>$contacts</td>
	</tr>};
}

print "\n</table>";
