git fetch origin dev

RESPONSE_FILE_CHANGED=$(git diff --name-status origin/dev | grep -c "response_schemas.py")
REQUEST_FILE_CHANGED=$(git diff --name-status origin/dev | grep -c "request_schemas.py")
API_CHANGELOG_CHANGED=$(git diff --name-status origin/dev | grep -c "api_changelog.md")

echo $RESPONSE_FILE_CHANGED
echo $REQUEST_FILE_CHANGED
echo $API_CHANGELOG_CHANGED

if [[ ( "$RESPONSE_FILE_CHANGED" -gt 0 || "$REQUEST_FILE_CHANGED"  -gt 0 ) && $API_CHANGELOG_CHANGED -eq 0 ]] ; then
	echo "Response schemas or request schemas have changed. Please update the API changelog. Is your change backward compatible?"
	exit 1
fi
