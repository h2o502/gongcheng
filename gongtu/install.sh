#!/bin/bash
# diagram skill - 一键自部署 Kroki Docker
# 用法: bash install.sh

set -e

KROKI_PORT="${KROKI_PORT:-8000}"

echo "🚀 自部署 Kroki 到 localhost:$KROKI_PORT"

if ! command -v docker &> /dev/null; then
    echo "❌ 未安装 Docker,请先安装 Docker"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# 停止旧容器(如果存在)
docker rm -f kroki 2>/dev/null || true

# 启动 Kroki
docker run -d \
    --name kroki \
    --restart unless-stopped \
    -p ${KROKI_PORT}:8000 \
    -e KROKI_SAFE_MODE=SECURE \
    -e KROKI_MERMAID_HOST=https://kroki.io \
    yuzutech/kroki

echo ""
echo "✅ Kroki 已启动: http://localhost:$KROKI_PORT"
echo ""
echo "设为默认渲染端点:"
echo "  export KROKI_ENDPOINT=http://localhost:$KROKI_PORT"
echo ""
echo "测试:"
echo "  echo 'Bob -> Alice : hello' | curl -X POST -H 'Content-Type: text/plain' \\"
echo "    --data-binary @- http://localhost:$KROKI_PORT/plantuml/svg -o test.svg"
echo ""
echo "查看日志: docker logs -f kroki"
echo "停止: docker stop kroki"
