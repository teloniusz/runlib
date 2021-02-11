echo "*** Relinking ***" >&2
dstroot="{subdir}"
dstdir="_installed_"
stage="{stage}"
envdir="{venv_dir}"

cd "$dstroot"
if [[ -d "$stage" ]]; then
    cd "$stage"
    {stop_cmd}
    cd - >/dev/null
fi
set -e
echo " ** Prepare cmd **" >&2
{prepare_cmd}
echo " ** Upgrade cmd **" >&2
{upgrade_cmd}
echo " ** Start cmd **" >&2
{start_cmd}
