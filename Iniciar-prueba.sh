#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
export STEAM_COMPAT_DATA_PATH='/home/nemesis/Documents/Codex/2026-11-13/tu-x20/work/proton-prefix'
export STEAM_COMPAT_CLIENT_INSTALL_PATH='/home/nemesis/.local/share/Steam'
export STEAM_COMPAT_APP_ID=0 SteamAppId=0 SteamGameId=0
exec '/home/nemesis/.local/share/Steam/steamapps/common/Proton - Experimental/proton' run './SPEED2.EXE'
