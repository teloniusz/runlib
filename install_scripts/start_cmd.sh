services=($(find . -name '*.service'))
if which systemctl >/dev/null && [[ ${services[0]} ]]; then
    mkdir -p ~/.config/systemd/user/
    cp *.service ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable *.service
    systemctl --user start *.service
else
    ./ctl uwsgi start
fi
