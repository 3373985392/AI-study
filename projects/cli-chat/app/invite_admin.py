"""仅供服务器管理员使用的邀请码管理命令。"""

import argparse
import getpass
import sqlite3
from datetime import datetime

from app.database import ChatDatabase
from app.security import secret_digest, validate_invite_code
from app.web_settings import load_web_settings


def positive_int(value: str) -> int:
    """供 argparse 使用的正整数校验器。"""

    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("额度必须大于或等于 1")
    return number


def format_time(value: int | None) -> str:
    return datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds") if value else "-"


def create_invite(args: argparse.Namespace, database: ChatDatabase) -> None:
    settings = load_web_settings()
    code = getpass.getpass("输入邀请码（不会显示）: ")
    confirmation = getpass.getpass("再次输入邀请码: ")
    if code != confirmation:
        raise SystemExit("两次输入的邀请码不一致")
    validate_invite_code(code)
    try:
        invite_id = database.create_invite(
            secret_digest(settings.invite_code_pepper, code),
            args.label,
            args.minute_limit or settings.minute_limit,
            args.day_limit or settings.day_limit,
        )
    except sqlite3.IntegrityError as error:
        raise SystemExit("该邀请码已经存在") from error
    print(f"邀请码已创建，ID: {invite_id}，明文不会被保存。")


def main() -> None:
    settings = load_web_settings()
    database = ChatDatabase(settings.database_path)
    parser = argparse.ArgumentParser(description="管理 Web Chat 邀请码")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="创建长期邀请码")
    create.add_argument("--label", required=True, help="便于管理员识别的备注")
    create.add_argument("--minute-limit", type=positive_int)
    create.add_argument("--day-limit", type=positive_int)

    subparsers.add_parser("list", help="列出邀请码（不显示明文）")
    for command in ("revoke", "activate", "stats"):
        action = subparsers.add_parser(command)
        action.add_argument("invite_id")

    args = parser.parse_args()
    if args.command == "create":
        create_invite(args, database)
    elif args.command == "list":
        for row in database.list_invites():
            status = "active" if row["active"] else "revoked"
            print(
                f"{row['id']}  {status:7}  {row['label']}  "
                f"limit={row['minute_limit']}/min,{row['day_limit']}/day  "
                f"last={format_time(row['last_used_at'])}"
            )
    elif args.command in {"revoke", "activate"}:
        active = args.command == "activate"
        if not database.set_invite_active(args.invite_id, active):
            raise SystemExit("找不到该邀请码 ID")
        print("邀请码已启用。" if active else "邀请码已撤销，已有会话已失效。")
    else:
        row = database.invite_stats(args.invite_id)
        if not row:
            raise SystemExit("找不到该邀请码 ID")
        print(
            f"ID={row['id']} label={row['label']} active={bool(row['active'])}\n"
            f"minute={row['minute_used']}/{row['minute_limit']} "
            f"day={row['day_used']}/{row['day_limit']} total={row['total_used']}\n"
            f"errors={row['error_count']} cancelled={row['cancelled_count']} "
            f"first_token_avg={row['average_first_token_ms'] or 0}ms "
            f"duration_avg={row['average_duration_ms'] or 0}ms\n"
            f"tokens={row['input_tokens']}in/{row['output_tokens']}out "
            f"estimated_cost_usd={row['estimated_cost_usd']:.6f}"
        )


if __name__ == "__main__":
    main()
