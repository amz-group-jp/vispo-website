#!/bin/sh
set -eu
cd "$(dirname "$0")"
vispo_mode=preview
case "${1:-}" in
  '') ;;
  --production) vispo_mode=production ;;
  *) echo 'Usage: ./deploy.sh [--production]' >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then echo 'Unexpected arguments' >&2; exit 2; fi
vispo_config_mode=$(python3 -c "import json; print(json.load(open('site-config.json')).get('mode', 'preview'))")
if [ "$vispo_config_mode" = production ] && [ "$vispo_mode" != production ]; then
  echo 'Production mode is configured. Use --production explicitly; refusing accidental noindex deployment.' >&2
  exit 2
fi
if [ "$vispo_mode" = production ] && [ "$vispo_config_mode" != production ]; then
  echo 'Complete the cutover checklist and set site-config.json mode to production before production deployment.' >&2
  exit 2
fi
python3 scripts/build.py --mode "$vispo_mode"
python3 scripts/verify.py --mode "$vispo_mode"
wrangler pages deploy dist --project-name vispo-website --branch main --commit-hash "$(git rev-parse HEAD)" --commit-message "Publish VISPO website"
