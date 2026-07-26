#!/usr/bin/env bash
# 校验每个 compose/<domain>/.env.<env> 里声明的镜像在 registry 上真实存在。
#
# 为什么需要这个: .env 里的镜像地址是手写的, 没有任何东西保证它和构建方
# 实际推送的路径一致。两者不一致时:
#
#   - compose 语法完全合法
#   - CI 全绿(CI 根本不拉镜像)
#   - Doco-CD 每 60s 拉一次、每次失败, 而它自己的容器一直 healthy
#   - docker ps 上什么异常都看不到
#
# 真实案例: .env.uat 按仓库名拼出
# ghcr.io/ai-workspace-infra/postgresql.svc.plus:latest, 而 CI 实际推到
# ghcr.io/x-evor/images/postgresql —— 整个 web-saas stack 拉不起来, 症状却
# 只是"accounts 连不上数据库"。
#
# 私有镜像匿名拉会得到 403(存在但无权限), 与 404(不存在)必须区分:
# 403 说明镜像在, 只是这里没凭据; 404 才是真的写错了地址。
set -euo pipefail

fail=0

check_image() {
  local var="$1" ref="$2"

  # 只带 digest 的引用没有 tag 可查, 跳过 —— digest 本身已经是不可变标识。
  if [[ "${ref}" == *"@sha256:"* ]]; then
    printf '  SKIP    %-22s %s (digest-pinned)\n' "${var}" "${ref}"
    return
  fi

  # 非 ghcr.io 的(如 docker.io 官方镜像)本脚本不查, 避免为每个 registry
  # 写一套鉴权。
  if [[ "${ref}" != ghcr.io/* ]]; then
    printf '  SKIP    %-22s %s (not ghcr.io)\n' "${var}" "${ref}"
    return
  fi

  local path="${ref#ghcr.io/}"
  local repo="${path%:*}"
  local tag="${path##*:}"
  [[ "${repo}" == "${tag}" ]] && tag=latest

  # 私有镜像匿名连 token 都换不到(GHCR 直接返回 UNAUTHORIZED), 所以带上
  # 凭据换 token。GHCR_USERNAME/GHCR_TOKEN 缺失时只能做匿名探测, 那样私有
  # 镜像一律查不出来 —— 这种情况下明确跳过并说明原因, 而不是报成"不存在",
  # 否则这个脚本自己就会变成一个误报来源。
  local token status auth=()
  if [[ -n "${GHCR_USERNAME:-}" && -n "${GHCR_TOKEN:-}" ]]; then
    auth=(-u "${GHCR_USERNAME}:${GHCR_TOKEN}")
  fi

  token="$(curl -sS "${auth[@]}" "https://ghcr.io/token?scope=repository:${repo}:pull&service=ghcr.io" | jq -r '.token // empty')"
  if [[ -z "${token}" ]]; then
    if [[ ${#auth[@]} -eq 0 ]]; then
      printf '  SKIP    %-22s %s (private; set GHCR_USERNAME/GHCR_TOKEN to check)\n' "${var}" "${ref}"
    else
      printf '  ERROR   %-22s %s (credentials rejected by registry)\n' "${var}" "${ref}"
      fail=1
    fi
    return
  fi

  status="$(curl -sS -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    -H 'Accept: application/vnd.oci.image.index.v1+json' \
    -H 'Accept: application/vnd.docker.distribution.manifest.list.v2+json' \
    -H 'Accept: application/vnd.docker.distribution.manifest.v2+json' \
    "https://ghcr.io/v2/${repo}/manifests/${tag}")"

  case "${status}" in
    200) printf '  OK      %-22s %s\n' "${var}" "${ref}" ;;
    403) printf '  PRIVATE %-22s %s (exists, needs credentials)\n' "${var}" "${ref}" ;;
    404) printf '  MISSING %-22s %s\n' "${var}" "${ref}"; fail=1 ;;
    *)   printf '  ERROR   %-22s %s (HTTP %s)\n' "${var}" "${ref}" "${status}"; fail=1 ;;
  esac
}

shopt -s nullglob
for env_file in compose/*/.env.*; do
  echo "=== ${env_file}"
  while read -r line; do
    # 用参数展开而不是 IFS='=' read: 镜像引用里可能含 '='(如 digest 形式),
    # IFS 切分会把它截断成一个拼不出正确 URL 的残缺值 —— 表现是每个镜像都
    # 报 "could not obtain a registry token", 看起来像网络或鉴权问题。
    var="${line%%=*}"
    ref="${line#*=}"
    check_image "${var}" "${ref}"
  done < <(grep -E '^[A-Z0-9_]+_IMAGE=' "${env_file}" || true)
done

if [[ "${fail}" -ne 0 ]]; then
  echo
  echo "One or more declared images do not exist in the registry." >&2
  echo "Nothing downstream reports this: compose stays valid, CI stays green," >&2
  echo "and Doco-CD retries forever while its own container looks healthy." >&2
  exit 1
fi

echo
echo "All declared images resolve."
