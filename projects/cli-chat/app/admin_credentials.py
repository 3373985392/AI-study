"""生成管理员密码哈希的服务器侧命令。"""

import argparse
import getpass

from app.admin_security import hash_admin_password


def main() -> None:
    parser = argparse.ArgumentParser(description="生成管理员 scrypt 密码哈希")
    parser.add_argument("command", choices=("hash",))
    parser.parse_args()

    password = getpass.getpass("输入管理员密码（至少 12 个字符）: ")
    confirmation = getpass.getpass("再次输入管理员密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致")
    try:
        encoded = hash_admin_password(password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print("将以下内容写入服务器环境文件：")
    print(f"ADMIN_PASSWORD_HASH={encoded}")


if __name__ == "__main__":
    main()
