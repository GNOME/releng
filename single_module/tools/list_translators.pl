#!/usr/bin/perl

use File::Slurp;

sub last_translator($) {
	my $pot = shift;

	my $content =  read_file ("po/$pot");
	my $translator = join ("", $content =~ m/Last-Translator:\s?([^<>]+?)\s?</sig);
	return $translator;
}

if (!$ARGV[0]) {
	print "usage: $0 LAST_RELEASE_TAG\n";
	exit 1;
}

my $cl=`cvs diff -r $ARGV[0] po/ChangeLog`;

@po = ($cl =~ m/[a-z][a-zA-Z@\_]*\.po/sig);

my @translators;

foreach $pot (@po) {
	my $found = 0;

	$last_trans = last_translator($pot);
	$string = "$last_trans: $pot";
	#print last_translator($pot).": $pot\n";
	foreach $trans (@translators) {
		if ($trans eq $string) {
			$found = 1;
		}
	}
	if ($found == 0) {
		push (@translators, $string);
	}
}

foreach $trans (@translators) {
	print "$trans\n";
}

