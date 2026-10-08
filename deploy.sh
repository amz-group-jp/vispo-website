#!/bin/sh
set -eu
cd "$(dirname "$0")"
vispo_deploy_dir=$(mktemp -d)
trap 'rm -rf "$vispo_deploy_dir"' EXIT HUP INT TERM
cp ./*.html ./style.css ./app.js ./_headers "$vispo_deploy_dir/"
cp -R ./assets "$vispo_deploy_dir/assets"
wrangler pages deploy "$vispo_deploy_dir" --project-name vispo-website --branch main --commit-hash "$(git rev-parse HEAD)" --commit-message "Publish VISPO website"
