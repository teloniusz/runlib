echo "*** Installing ***" >&2
dstroot={subdir}
dstdir=versions/{revision}
clean={clean}
replace={replace}

if [[ $clean = True ]]; then
    rroot=$(readlink -f $dstroot)
    linked=$(readlink -f "$rroot"/* | grep /versions/ | sort | uniq)
    echo " ** Attempting to remove all versions but: $linked and the newest" >&2
    for dir in $(ls -rtd $rroot/versions/* | grep -vxF "$linked" | sed -n -e :a -e '1!{{P;N;D;}};N;ba'); do
        rm -rI "$dir"
    done
fi
if [[ -d $dstroot/$dstdir && $replace = False ]]; then
    let sfx=1
    while [[ -d $dstroot/$dstdir.$sfx ]]; do let sfx++; done
    dstdir="$dstdir.$sfx"
fi
mkdir -pv "$dstroot/$dstdir" "$dstroot/shared/var"
ln -svfn "$dstdir" "$dstroot/_installed_"
