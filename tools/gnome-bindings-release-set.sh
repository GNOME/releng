#!/bin/bash
FTPROOT=/ftp/pub/GNOME
ERRORS=""

majmin() {
	echo $1 | sed "s#\([[:digit:]]\+\.[[:digit:]]\+\).*#\1#"
}

if [ -z "$1" ] || [ -z "$2" ] || [ ! -f "$3" ]; then
	echo "Usage: release <set> <version> <datafile>"
	exit 1
else
	RSET="$1"
	RVERSION="$2"
	RDATA="$3"
	
	RMAJMIN="$(majmin $RVERSION)"
	RDIR="$FTPROOT/$RSET/$RMAJMIN/$RVERSION/sources"
fi

if [ ! -d "$FTPROOT/$RSET" ]; then
	echo "There is no $RSET release!"
	exit 1
elif [ -d "$RDIR" ]; then
	echo "There is already a $RVERSION $RSET release!"
	exit 1
fi

# Create release directory
mkdir -p $RDIR
chmod g+ws $RDIR

# Read release data and create links
cat $RDATA | while read MDATA; do
	if [ ! -z "$MDATA" ]; then
		MODULE=$(echo $MDATA | cut -d : -f 1)
		VERSION=$(echo $MDATA | cut -d : -f 2)
		PROGRAMMING_LANGUAGE=$(echo $MDATA | cut -d : -f 3)		
		MAJMIN=$(majmin $VERSION)
		if [ -f $FTPROOT/sources/$MODULE/$MAJMIN/$MODULE-$VERSION.tar.gz ]; then
			# Create a link from the original in the sources directory. Put all modules for the same programming
			# language in their own sub-directory.
			ln -s ../../../../sources/$MODULE/$MAJMIN/$MODULE-$VERSION.tar.{gz,bz2} $RDIR/$PROGRAMMING_LANGUAGE
		else
			echo "$MODULE $VERSION is not available."
		fi
	fi
done

cd $RDIR
md5sum *.gz > MD5SUMS-for-gz
md5sum *.bz2 > MD5SUMS-for-bz2
chmod g+w $RDIR/MD5SUMS-for-*

# Print download sizss
echo
echo "Download statistics:"
echo "  tar.gz:   $(du -Lch *.tar.gz | grep total$)"
echo "  tar.bz2:  $(du -Lch *.tar.bz2 | grep total$)"
cd -
