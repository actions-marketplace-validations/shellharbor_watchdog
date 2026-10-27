#!/usr/bin/env bash
set -euo pipefail

(( $# == 2 )) || { printf 'Usage: sign-release.sh DIRECTORY vX.Y.Z\n' >&2; exit 2; }
artifact_directory="$1"
release_tag="$2"
[[ "$release_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || exit 2
[[ "${GITHUB_REPOSITORY:-}" == shellharbor/watchdog ]] || { printf 'Unexpected signing repository.\n' >&2; exit 2; }
[[ "${GITHUB_REF:-}" == "refs/tags/${release_tag}" ]] || { printf 'Signing must run on the release tag.\n' >&2; exit 2; }
identity="https://github.com/shellharbor/watchdog/.github/workflows/release-signing.yml@refs/tags/${release_tag}"
issuer='https://token.actions.githubusercontent.com'
archive="watchdog-${release_tag#v}.tar.gz"
cd -- "$artifact_directory"
[[ -f "$archive" && -f SHA256SUMS ]] || { printf 'Release artifacts are missing.\n' >&2; exit 2; }
sha256sum --check SHA256SUMS

verify_bundle() {
    cosign verify-blob --bundle "$2" --certificate-identity "$identity" \
        --certificate-oidc-issuer "$issuer" "$1"
}

for artifact in "$archive" SHA256SUMS; do
    cosign sign-blob --yes --bundle "${artifact}.sigstore.json" "$artifact"
    verify_bundle "$artifact" "${artifact}.sigstore.json"
done

# Verify all existing assets before any upload. A rerun can repair a partial
# upload, but cannot silently replace different bytes or an invalid signature.
existing_directory="$(mktemp -d "${TMPDIR:-/tmp}/watchdog-release-existing.XXXXXX")"
trap 'rm -rf -- "$existing_directory"' EXIT
existing_names="$(gh release view "$release_tag" --repo "$GITHUB_REPOSITORY" --json assets --jq '.assets[].name')"
declare -a missing=()
for artifact in "$archive" SHA256SUMS "${archive}.sigstore.json" SHA256SUMS.sigstore.json; do
    if grep -Fxq -- "$artifact" <<<"$existing_names"; then
        gh release download "$release_tag" --repo "$GITHUB_REPOSITORY" --pattern "$artifact" --dir "$existing_directory"
        if [[ "$artifact" == *.sigstore.json ]]; then
            verify_bundle "${artifact%.sigstore.json}" "${existing_directory}/${artifact}"
        else
            cmp --silent "$artifact" "${existing_directory}/${artifact}" || {
                printf 'Existing release artifact differs: %s\n' "$artifact" >&2
                exit 1
            }
        fi
    else
        missing+=("$artifact")
    fi
done
if (( ${#missing[@]} > 0 )); then
    gh release upload "$release_tag" --repo "$GITHUB_REPOSITORY" "${missing[@]}"
fi
printf 'Verified signed release assets for %s.\n' "$release_tag"
