real_dst=$(readlink -f "$dstdir")
real_stage=$(readlink -f "$stage")
venv_dir={venv_dir}
req_file={req_file}
if [[ $real_dst != "$real_stage" ]]; then
    if [[ -d "$stage/$venv_dir" && -f "$stage/$req_file" ]]; then
        if diff -q "$dstdir/$req_file" "$stage/$req_file"; then
            rsync -av "$stage/$venv_dir" "$dstdir/"
            for execfile in "$dstdir"/.venv/bin/*; do
                [[ $execfile = */python || $execfile = */python3 ]] && continue
                fline=$(head -1 "$execfile")
                for sfx in "$venv_dir/bin/python" "$venv_dir/bin/python3"; do
                    if [[ $fline = "#!$PWD"*"$sfx" ]]; then
                        to_replace="#!$real_dst/$sfx"
                        sed -i "1s~.*~$to_replace~" "$execfile"
                        break
                    fi
                done
            done
        fi
    fi
    ln -svfn "$real_dst" "$stage"
    [[ -d "env.$stage" ]] && rsync -Rav "env.$stage/./" "$stage"
    mkdir -p shared.$stage/var
    ln -svfn "$PWD/shared.$stage/var" "$stage/var"
fi

cd "$dstdir"
find . -type f -name \*.pyc -delete
./ctl env update
