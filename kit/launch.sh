#!/bin/sh
# launch.sh <repo-dir-name> <dispatch-file> <deadline HH:MM>  -> creates repo, room, sends dispatch, prints room id
set -eu
export PATH="$HOME/.local/bin:$HOME/.orbstack/bin:/opt/homebrew/bin:$PATH"
W=/Users/kinnu/hackathon4; REPO=$W/band-work/$1
mkdir -p $REPO && cd $REPO && git init -q -b main && mkdir -p mandates && cp $W/factory/mandates/*.md mandates/ && git add mandates && git -c user.name="Dhiraj" -c user.email="DKA137@SFU.CA" commit -q -m "Add seat mandates"
cd $W/band-work; R=$(band chat new --session seat-lead 2>/dev/null | grep -Eo '[0-9a-f]{8}-[0-9a-f-]{27}' | head -1)
for s in dhirajkavuri/builder dhirajkavuri/finisher dhirajkavuri/examiner dhirajkavuri/inspector bd07601c-f44a-4217-bada-f59738d453e4; do band chat add --session seat-lead $R $s >/dev/null 2>&1 || true; done
n=$(band room participants $R 2>/dev/null | grep -c "id=")
sed "s/__DEADLINE__/$3/" $W/factory/$2 > $W/band-work/checks/sent-$1.md
[ "$n" -ge 6 ] || { echo "participants=$n, not sending"; exit 1; }
docker info >/dev/null
band room send $R "$(cat $W/band-work/checks/sent-$1.md)" --mention 4c7a8541-89ff-4b32-a8b2-cadef5540314 >/dev/null 2>&1
echo $R > $W/factory/room-$1.txt; echo "room $R sent $(date +%H:%M:%S) participants $n"
