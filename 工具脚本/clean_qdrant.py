"""
清理 Qdrant 云端 Collection 脚本

用法:
    python 工具脚本/clean_qdrant.py              # 列出所有 collection
    python 工具脚本/clean_qdrant.py --all        # 清空所有 collection
    python 工具脚本/clean_qdrant.py --delete test rag_knowledge_base  # 删除指定 collection

如需通过代理访问 Qdrant，在 .env 中设置:
    QDRANT_PROXY=http://127.0.0.1:7897
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if not QDRANT_URL or not QDRANT_API_KEY:
    print("❌ 未找到 QDRANT_URL 或 QDRANT_API_KEY，请检查 .env 文件")
    sys.exit(1)

# --- 可选代理 ---
PROXY = os.getenv("QDRANT_PROXY", "")
if PROXY:
    os.environ["HTTP_PROXY"] = PROXY
    os.environ["HTTPS_PROXY"] = PROXY
    # Clash HTTP 代理做 MITM 时需跳过 SSL 验证
    os.environ["PYTHONHTTPSVERIFY"] = "0"
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    print(f"🌐 使用代理: {PROXY}")


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def list_collections(client: QdrantClient) -> list[str]:
    try:
        collections = client.get_collections().collections
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        sys.exit(1)

    if not collections:
        print("📭 没有找到任何 collection")
        return []
    print(f"📋 共 {len(collections)} 个 collection:\n")
    for c in collections:
        try:
            info = client.get_collection(c.name)
            print(f"  • {c.name:40s}  points: {info.points_count}")
        except Exception:
            print(f"  • {c.name:40s}  (无法获取详情)")
    print()
    return [c.name for c in collections]


def delete_collections(client: QdrantClient, names: list[str]):
    for name in names:
        try:
            client.delete_collection(name)
            print(f"🗑️  已删除: {name}")
        except Exception as e:
            print(f"⚠️  {name} 删除失败: {e}")


def main():
    args = sys.argv[1:]

    client = get_client()
    print(f"🔗 已连接 Qdrant: {QDRANT_URL}\n")

    if not args:
        list_collections(client)

    elif "--all" in args:
        names = list_collections(client)
        if not names:
            return
        confirm = input("⚠️  确认删除以上所有 collection？(y/N): ")
        if confirm.lower() == "y":
            delete_collections(client, names)
        else:
            print("已取消")

    elif "--delete" in args:
        idx = args.index("--delete")
        names = args[idx + 1:]
        if not names:
            print("❌ 请指定要删除的 collection 名称")
            sys.exit(1)
        delete_collections(client, names)

    else:
        print("用法:")
        print("  python 工具脚本/clean_qdrant.py              列出所有 collection")
        print("  python 工具脚本/clean_qdrant.py --all        清空所有 collection")
        print("  python 工具脚本/clean_qdrant.py --delete <name...>  删除指定 collection")


if __name__ == "__main__":
    main()
