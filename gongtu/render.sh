#!/bin/bash
# diagram skill - 渲染图源码为 SVG/PNG/PDF
# 用法: render.sh <type> <input> <output> [format]
# 示例: render.sh plantuml arch.puml arch.svg
#       render.sh mermaid flow.mmd flow.png
#
# 依赖: curl + Kroki 服务(默认公网,可自部署)
# 配置: 环境变量 KROKI_ENDPOINT,默认 https://kroki.io

set -e

TYPE="$1"
INPUT="$2"
OUTPUT="$3"
FORMAT="${4:-svg}"

if [ -z "$TYPE" ] || [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo "用法: render.sh <type> <input> <output> [format]"
    echo ""
    echo "参数:"
    echo "  type    图类型: plantuml / mermaid / d2 / graphviz / c4plantuml / excalidraw ..."
    echo "  input   源文件路径(.puml / .mmd / .d2 / .dot)"
    echo "  output  输出文件路径(.svg / .png / .pdf)"
    echo "  format  输出格式: svg(默认) / png / jpeg / pdf"
    echo ""
    echo "示例:"
    echo "  render.sh plantuml arch.puml arch.svg"
    echo "  render.sh mermaid flow.mmd flow.png"
    echo "  render.sh d2 system.d2 system.svg"
    exit 1
fi

if [ ! -f "$INPUT" ]; then
    echo "❌ 源文件不存在: $INPUT"
    exit 1
fi

KROKI_ENDPOINT="${KROKI_ENDPOINT:-https://kroki.io}"

# 从输出文件扩展名推断格式(如果没显式传)
if [ -z "$4" ]; then
    case "$OUTPUT" in
        *.svg) FORMAT=svg ;;
        *.png) FORMAT=png ;;
        *.jpg|*.jpeg) FORMAT=jpeg ;;
        *.pdf) FORMAT=pdf ;;
    esac
fi

echo "🔄 渲染中: $INPUT → $OUTPUT ($TYPE → $FORMAT)"

HTTP_CODE=$(curl -sS -w "%{http_code}" -X POST \
    -H "Content-Type: text/plain" \
    --data-binary @"$INPUT" \
    "${KROKI_ENDPOINT}/${TYPE}/${FORMAT}" \
    -o "$OUTPUT" 2>/dev/null) || true

if [ "$HTTP_CODE" = "200" ] && [ -s "$OUTPUT" ]; then
    # 校验输出完整性
    case "$FORMAT" in
        svg)
            if grep -q '</svg>' "$OUTPUT" 2>/dev/null; then
                SIZE=$(wc -c < "$OUTPUT")
                echo "✅ 渲染成功: $OUTPUT ($SIZE 字节)"
                echo "   类型: $TYPE | 格式: $FORMAT | 端点: $KROKI_ENDPOINT"
                exit 0
            else
                echo "❌ SVG 不完整,可能源码有语法错误"
                head -c 500 "$OUTPUT"
                exit 1
            fi
            ;;
        png|jpeg|pdf)
            SIZE=$(wc -c < "$OUTPUT")
            if [ "$SIZE" -gt 100 ]; then
                echo "✅ 渲染成功: $OUTPUT ($SIZE 字节)"
                echo "   类型: $TYPE | 格式: $FORMAT | 端点: $KROKI_ENDPOINT"
                exit 0
            else
                echo "❌ 输出文件过小,可能渲染失败"
                exit 1
            fi
            ;;
    esac
else
    echo "❌ 渲染失败 (HTTP $HTTP_CODE)"
    echo "   端点: ${KROKI_ENDPOINT}/${TYPE}/${FORMAT}"
    if [ -s "$OUTPUT" ]; then
        echo "   错误信息:"
        cat "$OUTPUT"
    fi
    exit 1
fi
