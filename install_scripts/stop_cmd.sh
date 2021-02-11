services=($(find . -name '*.service'))
if which systemctl >/dev/null && [[ ${services[0]} ]]; then
    systemctl --user status *.service
    systemctl --user stop *.service
else
    ./ctl uwsgi stop
fi
